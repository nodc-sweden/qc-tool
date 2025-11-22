from qc_tool.models.base_model import BaseModel
from qc_tool.visit import Visit


class VisitsModel(BaseModel):
    NEW_VISITS = "NEW_VISITS"
    VISIT_SELECTED = "VISIT_SELECTED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visits: dict[str, Visit] = {}
        self._selected_visit = None

    def set_visits(self, visits: dict[str, Visit]):
        self._visits = visits
        if self._visits:
            self._notify_listeners(self.NEW_VISITS)

    def set_visit(self, visit: Visit):
        print("set_visit")
        self._selected_visit = visit
        self._notify_listeners(self.VISIT_SELECTED)

    def set_visit_by_key(self, visit_key: str):
        print("set_visit_by_key")
        self.set_visit(self._visits[visit_key])

    @property
    def selected_visit(self) -> Visit:
        return self._selected_visit

    @property
    def visits(self) -> dict[str, Visit]:
        return self._visits

    def visit_by_index(self, index: int):
        return list(self._visits.values())[index]

    @property
    def visit_keys(self) -> list[str]:
        return [visit.visit_key for visit in self._visits.values()]

    @property
    def years(self) -> set[int]:
        return {visit.datetime.year for visit in self._visits.values()}

    @property
    def months(self) -> set[int]:
        return {visit.datetime.month for visit in self._visits.values()}

    @property
    def cruises(self) -> set[str]:
         return {visit.cruise_number for visit in self._visits.values()}

    @property
    def stations(self) -> set[str]:
        return {visit.station_name for visit in self._visits.values()}
