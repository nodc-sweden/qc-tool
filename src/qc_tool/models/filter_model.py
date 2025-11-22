from qc_tool.models.base_model import BaseModel


class FilterModel(BaseModel):
    FILTER_OPTIONS_CHANGED = "FILTER_OPTIONS_CHANGED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._years = set()
        self._months = set()
        self._cruises = set()
        self._stations = set()

    def clear_all(self):
        self._years = set()
        self._months = set()
        self._cruises = set()
        self._stations = set()

    def set_filter_options(self, years: set | None = None, months: set | None = None, stations: set | None = None, cruises: set | None = None):
        if years is not None:
            self._years = years
        if months is not None:
            self._months = months
        if stations is not None:
            self._stations = stations
        if cruises is not None:
            self._cruises = cruises

        self._notify_listeners(self.FILTER_OPTIONS_CHANGED)

    @property
    def years(self):
        return sorted(self._years)

    @property
    def months(self):
        return sorted(self._months)

    @property
    def stations(self):
        return sorted(self._stations)

    @property
    def cruises(self):
        return sorted(self._cruises)
