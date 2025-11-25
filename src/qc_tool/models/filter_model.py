from qc_tool.models.base_model import BaseModel
from qc_tool.visit import Visit


class FilterModel(BaseModel):
    FILTER_OPTIONS_CHANGED = "FILTER_OPTIONS_CHANGED"
    FILTER_CHANGED = "FILTER_CHANGED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._years = set()
        self._months = set()
        self._cruises = set()
        self._stations = set()
        self._filtered_years = set()
        self._filtered_months = set()
        self._filtered_cruises = set()
        self._filtered_stations = set()

    def clear_all(self):
        self._years = set()
        self._months = set()
        self._cruises = set()
        self._stations = set()
        self._filtered_months = set()
        self._filtered_cruises = set()
        self._filtered_stations = set()
        self._notify_listeners(self.FILTER_OPTIONS_CHANGED)

    def set_filter_options(
        self,
        years: set | None = None,
        months: set | None = None,
        cruises: set | None = None,
        stations: set | None = None,
    ):
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

    @property
    def filtered_stations(self) -> set[str]:
        return self._filtered_stations

    def set_year_filter(self, years):
        self._filtered_years = set(map(int, years))
        self._notify_listeners(self.FILTER_CHANGED)

    def set_month_filter(self, months):
        self._filtered_months = set(map(int, months))
        self._notify_listeners(self.FILTER_CHANGED)

    def set_cruise_filter(self, cruises):
        self._filtered_cruises = set(cruises)
        self._notify_listeners(self.FILTER_CHANGED)

    def set_station_filter(self, stations):
        self._filtered_stations = set(stations)
        self._notify_listeners(self.FILTER_CHANGED)

    def matches(
        self,
        visit: Visit,
        ignore_year: bool = False,
        ignore_month: bool = False,
        ignore_cruise: bool = False,
        ignore_station: bool = False,
    ):
        def _field_matches(value, filtered_values: set, ignore: bool):
            return ignore or not filtered_values or value in filtered_values

        return (
            _field_matches(visit.datetime.year, self._filtered_years, ignore_year)
            and _field_matches(visit.datetime.month, self._filtered_months, ignore_month)
            and _field_matches(visit.cruise_number, self._filtered_cruises, ignore_cruise)
            and _field_matches(
                visit.station_name, self._filtered_stations, ignore_station
            )
        )
