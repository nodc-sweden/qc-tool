from ocean_data_qc.fyskem.parameter import Parameter

from qc_tool.models.base_model import BaseModel


class ManualQcModel(BaseModel):
    VALUES_SELECTED = "VALUES_SELECTED"
    QC_PERFORMED = "QC_PERFORMED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parameter_index = None
        self._value_index = []
        self._selected_values: list[Parameter] = []
        self._last_sender = None

    @property
    def selected_values(self) -> list[Parameter]:
        return self._selected_values

    def set_selected_values(
        self, parameter_index, values: list[tuple[int, Parameter]], sender
    ):
        self._parameter_index = parameter_index
        self._value_index, self._selected_values = zip(*values)
        self._last_sender = sender
        self._notify_listeners(self.VALUES_SELECTED)

    def set_flag(self, new_flag):
        for value in self._selected_values:
            value.qc.manual = new_flag
        self._notify_listeners(self.QC_PERFORMED)
        self._last_sender.select_values(self._parameter_index, self._value_index)
