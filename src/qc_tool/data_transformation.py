import polars as pl
from ocean_data_qc.fyskem.qc_flag_tuple import QcField


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
        "visit_key",
        "LATIT",
        "LONGI",
        "STATN",
        "CTRYID",
        "SHIPC",
        "CRUISE_NO",
        "SERNO",
        "sample_date",
        "reported_sample_time",
        "sea_basin",
        "WADEP",
        "DEPH",
        "parameter",
        "value",
        "unit",
        "INCOMING_QC",
        "AUTO_QC",
        "MANUAL_QC",
        "TOTAL_QC",
        *auto_qc_columns,
    ]

    report_columns = [col for col in report_columns if col in data.columns]

    # Filter rows where incoming != total and select the feedback file columns
    return data.filter(incoming != total).select(report_columns)
