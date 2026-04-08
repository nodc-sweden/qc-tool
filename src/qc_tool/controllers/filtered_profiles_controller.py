from qc_tool.models.file_model import FileModel
from qc_tool.models.filter_model import FilterModel
from qc_tool.models.filtered_profiles_model import FilteredProfilesModel
from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.filtered_profiles_view import FilteredProfilesView


class FilteredProfilesController:
    def __init__(
        self,
        file_model: FileModel,
        visits_model: VisitsModel,
        filter_model: FilterModel,
        filtered_profiles_model: FilteredProfilesModel,
        manual_qc_model: ManualQcModel,
    ):
        self._file_model = file_model
        self._file_model.register_listener(FileModel.NEW_DATA, self._on_new_file)
        self._visits_model = visits_model
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._on_visit_selected
        )

        self._filter_model = filter_model
        self._filter_model.register_listener(
            FilterModel.FILTER_CHANGED,
            self._on_new_filter,
        )

        self._filtered_profiles_model = filtered_profiles_model
        self._filtered_profiles_model.register_listener(
            FilteredProfilesModel.NEW_SELECTION,
            self._on_new_parameter,
        )

        self._manual_qc_model = manual_qc_model
        self._manual_qc_model.register_listener(
            ManualQcModel.QC_PERFORMED, self._on_qc_performed
        )

        self.filtered_profiles_view: FilteredProfilesView = None

    def _on_new_file(self):
        self._filter_model.filtered_data = self._file_model.data
        self.filtered_profiles_view.update_grid_content(flag="file")

    def _on_visit_selected(self):
        self.filtered_profiles_view.update_grid_content(flag="visit")

    def _on_new_filter(self):
        self.filtered_profiles_view.update_grid_content(flag="filter")

    def _on_new_parameter(self):
        self.filtered_profiles_view.update_grid_content(flag="parameter")

    def _on_qc_performed(self):
        if self.filtered_profiles_view is None:
            return
        self.filtered_profiles_view.update_colors(self._manual_qc_model.selected_values)
