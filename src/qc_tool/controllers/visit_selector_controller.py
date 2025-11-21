from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.visit_selector_view import VisitSelectorView


class VisitSelectorController:
    def __init__(self, visits_model: VisitsModel):
        self._visits_model = visits_model
        self.visit_selector_view: VisitSelectorView = None

        self._visits_model.register_listener(VisitsModel.NEW_VISITS, self._new_visits)
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self.visit_selected
        )

    def _new_visits(self):
        self.visit_selector_view.update_visits()

    def set_visit(self, station_visit):
        self._visits_model.set_visit_by_key(station_visit)

    def visit_selected(self):
        self.visit_selector_view.set_visit(self._visits_model.selected_visit.visit_key)
