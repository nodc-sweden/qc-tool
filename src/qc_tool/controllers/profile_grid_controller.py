from qc_tool.models.manual_qc_model import ManualQcModel
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
        manual_qc_model: ManualQcModel,
    ):
        self._visits_model = visits_model
        self._visits_model.register_listener(
            (VisitsModel.VISIT_SELECTED, VisitsModel.UPDATED_VISITS),
            self._on_update_content,
        )

        self._profile_grid_model = profile_grid_model
        self._profile_grid_model.register_listener(
            ProfileGridModel.NEW_GRID_SIZE, self._on_new_grid_size
        )

        self._parameters_model = parameters_model
        self._parameters_model.register_listener(
            (ParametersModel.NEW_SELECTION, ParametersModel.NEW_PARAMETER_DATA),
            self._on_new_selection,
        )

        self._manual_qc_model = manual_qc_model
        self._manual_qc_model.register_listener(
            ManualQcModel.QC_PERFORMED, self._on_qc_performed
        )

        self._skip_next_update = False
        self.profile_grid_view: ProfileGridView = None

    def _on_update_content(self):
        if self.profile_grid_view is None:
            return
        if self._skip_next_update:
            self._skip_next_update = False
            return
        self._parameters_model.reset_parameter_data()
        self.profile_grid_view.update_grid_content()

    def _on_new_selection(self):
        if self.profile_grid_view is None:
            return
        self.profile_grid_view.update_grid_content()

    def _on_new_grid_size(self):
        first_new = self.profile_grid_view.update_grid_size()
        self.profile_grid_view.update_grid_content(start_index=first_new)

    def _on_qc_performed(self):
        if self.profile_grid_view is None:
            return
        self._skip_next_update = True
        self.profile_grid_view.update_colors(self._manual_qc_model.selected_values)
