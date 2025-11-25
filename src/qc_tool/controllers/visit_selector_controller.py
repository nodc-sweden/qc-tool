from qc_tool.models.filter_model import FilterModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.visit_selector_view import VisitSelectorView


class VisitSelectorController:
    def __init__(self, visits_model: VisitsModel, filter_model: FilterModel):
        self.visit_selector_view: VisitSelectorView = None

        self._visits_model = visits_model
        self._visits_model.register_listener(
            (VisitsModel.NEW_VISITS, VisitsModel.UPDATED_VISITS), self._on_new_visits
        )
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._on_visit_selected
        )
        self._visits_model.register_listener(
            VisitsModel.FILTER_APPLIED, self._on_new_visits
        )

        self._filter_model = filter_model
        self._filter_model.register_listener(
            FilterModel.FILTER_CHANGED, self._on_filter_changed
        )

    def _on_new_visits(self):
        self.visit_selector_view.update_visits()

    def _on_filter_changed(self):
        if (
            self._visits_model.selected_visit
            and self._visits_model.selected_visit.visit_key
            not in self._visits_model.visit_keys
        ) or (self._visits_model.visit_keys and not self._visits_model.selected_visit):
            new_visit = self._visits_model.first_visit_id_or_none()
            self._visits_model.set_visit_by_key(new_visit)

    def set_visit(self, station_visit):
        self._visits_model.set_visit_by_key(station_visit)

    def _on_visit_selected(self):
        self.visit_selector_view.set_visit(
            self._visits_model.selected_visit.visit_key
            if self._visits_model.selected_visit
            else ""
        )
