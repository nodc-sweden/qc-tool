import polars as pl
from ocean_data_qc.fyskem.parameter import Parameter

from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.models.visits_model import VisitsModel


class ManualQcController:
    def __init__(self, manual_qc_model: ManualQcModel, visits_model: VisitsModel):
        self.manual_qc_model = manual_qc_model
        self._visits_model = visits_model
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._on_visit_selected
        )
        self._visits_model.register_listener(
            VisitsModel.UPDATED_VISITS, self._on_visit_selected
        )
        self.manual_qc_view = None

    def _on_visit_selected(self):
        if self.manual_qc_view is None:
            return
        visit = self._visits_model.selected_visit
        depths = [str(d) for d in visit.depths] if visit else []
        parameters = visit.parameters if visit else []
        self.manual_qc_view.update_depths(depths)
        self.manual_qc_view.update_parameters(parameters)

    def on_filter_changed(
        self, selected_depths: list[str], selected_parameters: list[str]
    ):
        visit = self._visits_model.selected_visit
        if visit is None or (not selected_depths and not selected_parameters):
            self.manual_qc_model.set_values_from_filter([])
            return

        data = visit.data
        if selected_depths:
            depth_floats = [float(d) for d in selected_depths]
            data = data.filter(pl.col("DEPH").is_in(depth_floats))
        if selected_parameters:
            data = data.filter(pl.col("parameter").is_in(selected_parameters))

        values = [Parameter(row) for row in data.iter_rows(named=True)]
        self.manual_qc_model.set_values_from_filter(values)

    def deselect_value(self, index: int):
        self.manual_qc_model.deselect_value(index)

    def set_flag(self):
        self.manual_qc_model.request_flag()
