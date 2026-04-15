from qc_tool.models.file_model import FileModel
from qc_tool.models.filter_model import FilterModel
from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.models.scatter_model import ScatterModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.scatter_view import ScatterView


class ScatterController:
    def __init__(
        self,
        file_model: FileModel,
        visits_model: VisitsModel,
        filter_model: FilterModel,
        scatter_model: ScatterModel,
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

        self._scatter_model = scatter_model
        self._scatter_model.register_listener(
            ScatterModel.NEW_SELECTION,
            self._on_new_parameter,
        )

        self._manual_qc_model = manual_qc_model
        self._manual_qc_model.register_listener(
            ManualQcModel.QC_PERFORMED, self._on_qc_performed
        )

        self.scatter_view: ScatterView = None

    def _on_new_file(self):
        self._filter_model.filtered_data = self._file_model.data
        self.scatter_view.update_grid_content(flag="file")

    def _on_visit_selected(self):
        self.scatter_view.update_grid_content(flag="visit")

    def _on_new_filter(self):
        self.scatter_view.update_grid_content(flag="filter")

    def _on_new_parameter(self):
        self.scatter_view.update_grid_content(flag="parameter")

    def _on_qc_performed(self):
        if self.scatter_view is None:
            return
        self.scatter_view.update_colors(self._manual_qc_model.selected_values)
