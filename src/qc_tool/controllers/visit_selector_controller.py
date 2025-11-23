from qc_tool.models.filter_model import FilterModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.visit_selector_view import VisitSelectorView


class VisitSelectorController:
    def __init__(self, visits_model: VisitsModel, filter_model: FilterModel):
        self.visit_selector_view: VisitSelectorView = None

        self._visits_model = visits_model
        self._visits_model.register_listener(VisitsModel.NEW_VISITS, self._on_new_visits)
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self.visit_selected
        )

        self._filter_model = filter_model
        self._filter_model.register_listener(FilterModel.FILTER_CHANGED, self._on_filter_changed)

    @property
    def filtered_visits(self):
        filtered_visits = []
        for visit in self._visits_model.visits.values():
            if self._filter_model.filtered_stations and visit.station_name not in self._filter_model.filtered_stations:
                continue
            filtered_visits.append(visit.visit_key)
        print(f"filtered_visits: {filtered_visits}")
        return filtered_visits

    def _on_new_visits(self):
        self.visit_selector_view.update_visits()

    def _on_filter_changed(self):
        print("visit_selector_controller._on_filter_changed")
        self.visit_selector_view.update_visits()
        if self._visits_model.selected_visit and self._visits_model.selected_visit.visit_key not in self.filtered_visits:
            self._visits_model.set_visit_by_key(self.filtered_visits[0])

    def set_visit(self, station_visit):
        self._visits_model.set_visit_by_key(station_visit)

    def visit_selected(self):
        self.visit_selector_view.set_visit(self._visits_model.selected_visit.visit_key)
