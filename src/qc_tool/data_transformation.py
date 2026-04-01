from collections import Counter, defaultdict
from pathlib import Path

import polars as pl
from ocean_data_qc.fyskem.qc_flag_tuple import QcField
from sharkadm import validators


def get_validators_in_log(log):
    validators_map = {}

    for row in log:
        name = row.get("validator", "no validator")
        cls_name = row.get("cls")

        if name not in validators_map and cls_name:
            validators_map[name] = getattr(validators, cls_name)

    return validators_map


def collect_log_messages(log: list):
    log_messages = defaultdict(
        lambda: {
            "messages": defaultdict(list),
        }
    )

    for row in log:
        level = row.get("level", "info")

        # Only include relevant levels
        if level not in ("error", "warning", "critical"):
            continue

        validator_name = row.get("validator", "no validator")
        column = row.get("column") or "General"

        log_messages[validator_name]["messages"][column].append(row["msg"])

    available_validators = get_validators_in_log(log)

    for validator_name, data in log_messages.items():
        # Count ALL messages
        data["count"] = sum(len(msgs) for msgs in data["messages"].values())

        # Add description
        validator_cls = available_validators.get(validator_name)
        if validator_cls:
            data["description"] = validator_cls.get_validator_description()
        else:
            data["description"] = ""

    return log_messages


def remove_lims(parts: tuple[str, ...]) -> tuple[str, ...]:
    if parts[-2:] == ("Raw_data", "data.txt"):
        return parts[:-2]
    return parts


def shortest_unique_paths(paths: list[Path]) -> dict[Path, str]:
    if not paths:
        return {}
    effective_parts = {path: remove_lims(path.parts) for path in paths}
    path_mapping = {path: parts[-1:] for path, parts in effective_parts.items()}
    collisions = True
    while collisions:
        collisions = False
        collision_counter = Counter(path_mapping.values())
        duplicat_path, count = max(collision_counter.items(), key=lambda x: x[1])
        if count > 1:
            collisions = True
            for path, parts in path_mapping.items():
                if parts == duplicat_path:
                    path_mapping[path] = effective_parts[path][-len(parts) - 1 :]
    return {
        path: f"{n}. {Path(*parts)}"
        for n, (path, parts) in enumerate(path_mapping.items(), start=1)
    }


def prepare_data(data: pl.DataFrame):
    # Create the long qc string using "quality_flag" as incoming qc
    if "quality_flag_long" not in data.columns and "quality_flag" in data.columns:
        auto_flags = f"_{'0' * len(QcField)}_0_"
        data = data.with_columns(
            pl.concat_str(
                [
                    pl.col("quality_flag"),
                    pl.lit(auto_flags),
                    pl.col("quality_flag"),
                ]
            ).alias("quality_flag_long")
        )
    # Normalize SERNO
    data = data.with_columns(
        (
            data["SERNO"]
            .cast(pl.Float64, strict=False)
            .round(0)
            .cast(pl.Int64, strict=False)
            .fill_null(-1)
            .cast(pl.Utf8)
            .str.zfill(4)
            .replace("-001", None)
        ).alias("SERNO")
    )
    return data


def changes_report(data: pl.DataFrame) -> pl.DataFrame:
    # Extract first (incoming) and last (total) parts of quality_flag_long
    incoming = pl.col("quality_flag_long").str.split("_").list.get(0)
    total = pl.col("quality_flag_long").str.split("_").list.get(-1)

    # Find all automatic QC columns dynamically
    auto_qc_columns = [c for c in data.columns if "total_automatic" in c]

    # Columns to include in the feedback file
    # visit_key is needed to be able to merge feedback file later on
    report_columns = [
        "SERNO",
        "reported_visit_date",
        "visit_key",
        "STATN",
        "reported_sample_depth_m",
        "parameter",
        "reported_value",
        "INCOMING_QC",
        "AUTO_QC",
        "MANUAL_QC",
        "MANUAL_QC_CATEGORY",
        "MANUAL_QC_COMMENT",
        "TOTAL_QC",
        *auto_qc_columns,
    ]

    report_columns = [col for col in report_columns if col in data.columns]

    rename_map = {
        "reported_visit_date": "SDATE",
        "reported_sample_depth_m": "DEPH",
        "reported_value": "value",
    }

    # Filter rows where incoming != total and select the feedback file columns
    condition = incoming != total
    if "total_automatic" in data.columns:
        condition &= pl.col("total_automatic") != "Probably good value"

    return data.filter(condition).select(report_columns).rename(rename_map)
