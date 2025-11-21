from qc_tool.models.file_model import FileModel
from qc_tool.models.parameters_model import ParametersModel
from qc_tool.models.profiles_grid_model import ProfileGridModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.parameter_selector_view import ParameterSelectorView


class ParameterSelectorController:
    def __init__(
        self,
        visits_model: VisitsModel,
        parameters_model: ParametersModel,
        profile_grid_model: ProfileGridModel,
        file_model: FileModel,
    ):
        self._visits_model = visits_model
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._on_visit_selected
        )

        self._parameters_model = parameters_model

        self._file_model = file_model
        self._file_model.register_listener(FileModel.NEW_DATA, self._on_new_data)

        self._profiles_model = profile_grid_model
        self._profiles_model.register_listener(
            ProfileGridModel.NEW_GRID_SIZE, self._on_new_grid_size
        )

        self.parameter_selector_view: ParameterSelectorView = None

    def _on_new_grid_size(self):
        self._parameters_model.selected_parameters = (
            self._parameters_model.selected_parameters[
                : self._profiles_model.number_of_profiles
            ]
        )
        self.parameter_selector_view.update_parameters()

    def _on_new_data(self):
        self._parameters_model.set_default_parameters()

    def _on_visit_selected(self):
        print("_on_visit_selected")
        self._parameters_model.available_parameters = (
            self._visits_model.selected_visit.parameters
        )
        self.parameter_selector_view.update_parameters()

    def select_parameters(self, selection):
        if not selection:
            return None
        if (
            len(selection) + self._parameters_model.selection_size
            > self._profiles_model.number_of_profiles
        ):
            return None

        self.parameter_selector_view.clear_all_selections()
        self._parameters_model.selected_parameters += selection
        self.parameter_selector_view.update_parameters()

    def deselect_parameters(self, selection):
        if not selection:
            return None
        self.parameter_selector_view.clear_all_selections()
        self._parameters_model.selected_parameters = [
            parameter
            for parameter in self._parameters_model._selected_parameters
            if parameter not in set(selection)
        ]
        self.parameter_selector_view.update_parameters()

    def move_selection_up(self, selection):
        if not selection:
            return None

        new_selection = self._parameters_model.selected_parameters[:]
        for n, v in enumerate(new_selection[1:], start=1):
            if v in selection and new_selection[n - 1] not in selection:
                new_selection[n - 1], new_selection[n] = (
                    new_selection[n],
                    new_selection[n - 1],
                )
        self._parameters_model.selected_parameters = new_selection
        self.parameter_selector_view.update_parameters()

    def move_selection_down(self, selection):
        if not selection:
            return None

        new_selection = self._parameters_model.selected_parameters[:]
        for n, v in reversed(list(enumerate(new_selection[:-1]))):
            if v in selection and new_selection[n + 1] not in selection:
                new_selection[n], new_selection[n + 1] = (
                    new_selection[n + 1],
                    new_selection[n],
                )
        self._parameters_model.selected_parameters = new_selection
        self.parameter_selector_view.update_parameters()

    def set_columns(self, columns: int):
        self._profiles_model.columns = columns

    def set_rows(self, rows: int):
        self._profiles_model.rows = rows
