from qc_tool.app_state import AppState
from qc_tool.controllers.manual_qc_controller import ManualQcController
from qc_tool.controllers.map_controller import MapController
from qc_tool.controllers.parameter_selector_controller import ParameterSelectorController
from qc_tool.controllers.profile_grid_controller import ProfileGridController
from qc_tool.controllers.visit_info_controller import VisitInfoController
from qc_tool.controllers.visit_selector_controller import VisitSelectorController
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.visits_browser_view import VisitsBrowserView


class VisitsBrowserController:
    def __init__(self, state: AppState):
        self._state = state

        # TODO: This should be moved to a controller for scatter plots
        self._visits_model = state.visits
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._on_visit_selected
        )

        self.map_controller = MapController(self._state.visits, self._state.map)
        self.visit_selector_controller = VisitSelectorController(
            self._state.visits, self._state.filter
        )

        self.visit_info_controller = VisitInfoController(self._state.visits)
        self.parameter_selector_controller = ParameterSelectorController(
            self._state.visits,
            self._state.parameters,
            self._state.profile_grid,
            self._state.file,
        )
        self.profile_grid_controller = ProfileGridController(
            self._state.visits, self._state.profile_grid, self._state.parameters
        )

        self.manual_qc_controller = ManualQcController(self._state.manual_qc)

        self.visits_browser_view: VisitsBrowserView = None

    def _on_visit_selected(self):
        self.visits_browser_view.update_scatter_plots()
