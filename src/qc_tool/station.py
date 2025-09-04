import datetime

import polars as pl
from ocean_data_qc.metadata.visit import Visit
from ocean_data_qc.metadataqc import MetadataQc


class Station:
    COMMON_COLUMNS = frozenset(
        {
            "AIRPRES",
            "AIRTEMP",
            "COMNT_VISIT",
            "CRUISE_NO",
            "CTRYID",
            "DEPH",
            "LATIT",
            "LONGI",
            "SDATE",
            "SHIPC",
            "STATN",
            "STIME",
            "SERNO",
            "WADEP",
            "WINDIR",
            "WINSP",
        }
    )

    def __init__(self, visit_key: str, data: pl.DataFrame, geo_info):
        self._visit_key = visit_key
        self._data = data

        self._common = {
            column: self._data[column].unique().to_list()[0]
            for column in self.COMMON_COLUMNS
            if column in self._data.columns
        }

        self._parameters = sorted(self._data["parameter"].unique().to_list())

        if "sea_basin" in self._data.columns:
            self._sea_basin = self._data["sea_basin"].unique().to_list()[0]
        else:
            self._sea_basin = None

        self._visit = Visit(self.data)

    def run_metadata_qc(self):
        metadata_qc = MetadataQc(self._visit)
        metadata_qc.run_qc()

    @property
    def parameters(self) -> list[str]:
        return self._parameters

    @property
    def sea_basin(self):
        return self._sea_basin

    @property
    def data(self) -> pl.DataFrame:
        return self._data

    @property
    def datetime(self):
        return self._data.select("datetime").to_series()[0]

    @property
    def country_ship_cruise_visit_key(self):
        return "-".join(
            [str(self._common.get(key)) for key in ("CTRYID", "SHIPC", "CRUISE_NO")]
            + [self._visit_key]
        )

    @property
    def country_ship_cruise(self):
        return "-".join(
            [str(self._common.get(key)) for key in ("CTRYID", "SHIPC", "CRUISE_NO")]
        )

    @property
    def visit_key(self):
        return self._visit_key

    @property
    def common(self):
        compound_values = {
            "SDATE+STIME": self.datetime,
            "CTRYID+SHIPC+CRUISE_NO+VISITKEY": self.country_ship_cruise_visit_key,
            "CTRYID+SHIPC+CRUISE_NO": self.country_ship_cruise,
        }
        return self._common | compound_values

    @property
    def water_depth(self):
        return self._common.get("WADEP")

    @property
    def longitude(self):
        degrees, remainder = divmod(self._common.get("LONGI"), 100)
        return degrees + remainder / 60

    @property
    def latitude(self):
        degrees, remainder = divmod(self._common.get("LATIT"), 100)
        return degrees + remainder / 60
