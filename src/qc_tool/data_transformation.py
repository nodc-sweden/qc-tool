import pandas as pd
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
    return data


def changes_report(data: pd.DataFrame):
    # Create dataframe with rows only where qc_incoming and qc_total differ
    incoming = data["quality_flag_long"].str.split("_").str[0]
    total = data["quality_flag_long"].str.split("_").str[-1]
    auto_qc_columns = [column for column in data.columns if "automatic" in column]
    report_columns = [
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

    return data[incoming != total][report_columns]
