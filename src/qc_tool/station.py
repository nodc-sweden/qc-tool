import datetime


class Station:
    COMMON_COLUMNS = {
        "AIRPRES",
        "AIRTEMP",
        "COMNT_VISIT",
        "CTRYID-SHIPC-CRUISE_NO-STNNO",
        "CRUISE_NO",
        "CTRYID",
        "DEPH",
        "LATIT",
        "LONGI",
        "SDATE",
        "SHIPC",
        "STATN",
        "STIME",
        "STNNO",
        "WADEP",
        "WINDR",
        "WINSP",
    }

    def __init__(self, series: str, data):
        self._series = series
        self._data = data
        all_parameters = set(data.dropna(axis=1, how="all").columns)
        self._common = {
            column: self._data[column].unique()[0]
            for column in all_parameters & self.COMMON_COLUMNS
        }

        self._parameters = sorted(all_parameters - self.COMMON_COLUMNS)

    @property
    def parameters(self) -> list[str]:
        return self._parameters

    @property
    def data(self):
        return self._data

    @property
    def datetime(self):
        date_string = self._common.get("SDATE")
        time_string = self._common.get("STIME")
        try:
            date = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
            time = datetime.datetime.strptime(time_string, "%H:%M").time()
        except ValueError:
            return None
        return datetime.datetime.combine(date, time)

    @property
    def country_ship_cruise_series(self):
        return "-".join(
            [str(self._common.get(key)) for key in ("CTRYID", "SHIPC", "CRUISE_NO")]
            + [self._series]
        )

    @property
    def series(self):
        return self._series

    @property
    def common(self):
        compound_values = {
            "SDATE+STIME": self.datetime,
            "CTRYID+SHIPC+CRUISE_NO+STNNO": self.country_ship_cruise_series,
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
