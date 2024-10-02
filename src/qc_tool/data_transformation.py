import pandas as pd
from ocean_data_qc.fyskem.qc_flag_tuple import QcField


def prepare_data(data: pd.DataFrame):
    # Create station name with zero padded serial number
    data["SERNO"] = data["SERNO"].map("{:03}".format)

    # Create the long qc string using "quality_flag" as incoming qc
    if "quality_flag_long" not in data.columns and "quality_flag" in data.columns:
        data["quality_flag_long"] = data["quality_flag"] + f"_{'0' * len(QcField)}_0"
    return data
