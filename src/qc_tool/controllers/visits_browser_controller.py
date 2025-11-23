from qc_tool.app_state import AppState
from qc_tool.controllers.map_controller import MapController
from qc_tool.controllers.parameter_selector_controller import ParameterSelectorController
from qc_tool.controllers.profile_grid_controller import ProfileGridController
from qc_tool.controllers.visit_info_controller import VisitInfoController
from qc_tool.controllers.visit_selector_controller import VisitSelectorController
from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.views.visits_browser_view import VisitsBrowserView


class VisitsBrowserController:
    def __init__(self, state: AppState):
        self._state = state
        self._manual_qc_model = state.manual_qc
        self._manual_qc_model.register_listener(
            ManualQcModel.VALUES_SELECTED, self._on_values_selected
        )

        self.map_controller = MapController(self._state.visits, self._state.map)
        self.visit_selector_controller = VisitSelectorController(self._state.visits, self._state.filter)
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

        self.visits_browser_view: VisitsBrowserView = None

    def _on_values_selected(self):
        if self._manual_qc_model.selected_values:
            self.visits_browser_view._extra_info_tabs.active = 1
