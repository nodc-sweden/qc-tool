import pandas as pd
from ocean_data_qc.fyskem.qc_flag_tuple import QcField


def prepare_data(data: pd.DataFrame):
    # Create station name with zero padded serial number
    data["SERNO"] = data["SERNO"].map("{:03}".format)

    # Create the long qc string using "quality_flag" as incoming qc
    if "quality_flag_long" not in data.columns and "quality_flag" in data.columns:
        data["quality_flag_long"] = (
            data["quality_flag"] + f"_{'0' * len(QcField)}_0_" + data["quality_flag"]
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
