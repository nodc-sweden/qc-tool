from qc_tool.models.base_model import BaseModel
from qc_tool.models.filter_model import FilterModel
from qc_tool.visit import Visit


class VisitsModel(BaseModel):
    NEW_VISITS = "NEW_VISITS"
    UPDATED_VISITS = "UPDATED_VISITS"
    VISIT_SELECTED = "VISIT_SELECTED"
    FILTER_APPLIED = "FILTER_APPLIED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visits: dict[str, Visit] = {}
        self._filtered_stations = None
        self._selected_visit = None

    def set_visits(self, visits: dict[str, Visit]):
        self._visits = visits
        self._filtered_stations = None
        if self._visits:
            self._notify_listeners(self.NEW_VISITS)

    def update_visits(self, visits: dict[str, Visit]):
        self._visits = visits
        self._selected_visit = self._visits.get(self._selected_visit.visit_key)
        self._notify_listeners(self.UPDATED_VISITS)

    def set_visit(self, visit: Visit | None):
        self._selected_visit = visit
        self._notify_listeners(self.VISIT_SELECTED)

    def set_visit_by_key(self, visit_key: str):
        self.set_visit(self._visits.get(visit_key))

    def apply_filter(self, filter_model: FilterModel):
        self._filtered_stations = {
            visit.visit_key
            for visit in self._visits.values()
            if filter_model.matches(visit)
        }
        self._notify_listeners(self.FILTER_APPLIED)

    @property
    def selected_visit(self) -> Visit:
        return self._selected_visit

    @property
    def visits(self) -> dict[str, Visit]:
        if self._filtered_stations is None:
            return self._visits
        return {
            key: value
            for key, value in self._visits.items()
            if key in self._filtered_stations
        }

    def visit_by_index(self, index: int):
        return list(self._visits.values())[index]

    def first_visit_or_none(self) -> Visit | None:
        if self._visits:
            return next(iter(self._visits.values()))
        return None

    def first_visit_id_or_none(self) -> str | None:
        available_visits = self.visits
        if available_visits:
            return next(iter(available_visits))
        return None

    @property
    def visit_keys(self) -> list[str]:
        if self._filtered_stations is not None:
            return [visit for visit in self._visits if visit in self._filtered_stations]
        return list(self._visits.keys())

    @property
    def years(self) -> set[int]:
        return {visit.datetime.year for visit in self.visits.values()}

    @property
    def months(self) -> set[int]:
        return {visit.datetime.month for visit in self.visits.values()}

    @property
    def cruises(self) -> set[str]:
        return {visit.cruise_number for visit in self.visits.values()}

    @property
    def stations(self) -> set[str]:
        return {visit.station_name for visit in self.visits.values()}

    def possible_years(self, filter_model: FilterModel):
        return {
            visit.datetime.year
            for visit in self._visits.values()
            if filter_model.matches(visit, ignore_year=True)
        }

    def possible_months(self, filter_model: FilterModel):
        return {
            visit.datetime.month
            for visit in self._visits.values()
            if filter_model.matches(visit, ignore_month=True)
        }

    def possible_cruises(self, filter_model: FilterModel):
        return {
            visit.cruise_number
            for visit in self._visits.values()
            if filter_model.matches(visit, ignore_cruise=True)
        }

    def possible_stations(self, filter_model: FilterModel):
        return {
            visit.station_name
            for visit in self._visits.values()
            if filter_model.matches(visit, ignore_station=True)
        }
