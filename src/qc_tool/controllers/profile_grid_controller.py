from qc_tool.models.parameters_model import ParametersModel
from qc_tool.models.profiles_grid_model import ProfileGridModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.profile_grid_view import ProfileGridView


class ProfileGridController:
    def __init__(
        self,
        visits_model: VisitsModel,
        profile_grid_model: ProfileGridModel,
        parameters_model: ParametersModel,
    ):
        self._visits_model = visits_model
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._on_visit_selected
        )

        self._profile_grid_model = profile_grid_model
        self._profile_grid_model.register_listener(
            ProfileGridModel.NEW_GRID_SIZE, self._on_new_grid_size
        )

        self._parameters_model = parameters_model
        self._parameters_model.register_listener(
            ParametersModel.NEW_SELECTION, self._on_new_selection
        )

        self.profile_grid_view: ProfileGridView = None

    def _on_visit_selected(self):
        self.profile_grid_view.update_grid_content()

    def _on_new_selection(self):
        print("profile_grid_controller._on_new_selection")
        self.profile_grid_view.update_grid_content()

    def _on_new_grid_size(self):
        self.profile_grid_view.update_grid_size()
        self.profile_grid_view.update_grid_content()
