from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskem.qc_flag import QcFlag

from qc_tool.models.base_model import BaseModel


class ManualQcModel(BaseModel):
    VALUES_SELECTED = "VALUES_SELECTED"
    QC_PERFORMED = "QC_PERFORMED"
    FLAG_REQUESTED = "FLAG_REQUESTED"
    FLAG_CANCELLED = "FLAG_CANCELLED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parameter_index = None
        self._value_index = []
        self._selected_values: list[Parameter] = []
        self._last_sender = None
        self._comment_category: str = ""
        self._comment: str = ""

    @property
    def selected_values(self) -> list[Parameter]:
        return self._selected_values

    @property
    def comment_category(self) -> str:
        return self._comment_category

    @property
    def comment(self) -> str:
        return self._comment

    def set_selected_values(
        self, parameter_index, values: list[tuple[int, Parameter]], sender
    ):
        self._parameter_index = parameter_index
        self._value_index, self._selected_values = zip(*values)
        self._last_sender = sender
        self._notify_listeners(self.VALUES_SELECTED)

    def set_values_from_filter(self, values: list[Parameter]):
        self._selected_values = values
        self._last_sender = None
        self._notify_listeners(self.VALUES_SELECTED)

    def request_flag(self):
        self._notify_listeners(self.FLAG_REQUESTED)

    def confirm_flag(self, flag: QcFlag, category: str, comment: str):
        if not self._selected_values:
            return
        self._comment_category = category
        self._comment = comment
        for value in self._selected_values:
            value.qc.manual = flag
            value._data["MANUAL_QC_CATEGORY"] = category
            value._data["MANUAL_QC_COMMENT"] = comment
        self._notify_listeners(self.QC_PERFORMED)
        if self._last_sender is not None:
            self._last_sender.select_values(self._parameter_index, self._value_index)

    def deselect_value(self, index: int):
        self._selected_values = [
            v for i, v in enumerate(self._selected_values) if i != index
        ]
        self._notify_listeners(self.VALUES_SELECTED)

    def cancel_flag(self):
        self._notify_listeners(self.FLAG_CANCELLED)
