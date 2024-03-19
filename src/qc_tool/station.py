class Station:
    COMMON_COLUMNS = {
        "COMNT_VISIT",
        "WADEP",
        "STATN",
        "WINDR",
        "WINSP",
        "AIRTEMP",
        "AIRPRES",
        "LONGI",
        "LATIT",
    }

    def __init__(self, name: str, data):
        self._name = name
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
    def name(self):
        return self._name

    @property
    def common(self):
        return self._common

    @property
    def water_depth(self):
        return self._common.get("WADEP")

    @property
    def longitude(self):
        return self._common.get("LONGI") / 100

    @property
    def latitude(self):
        return self._common.get("LATIT") / 100
