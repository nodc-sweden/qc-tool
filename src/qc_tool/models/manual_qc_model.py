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
        self._pending_flag: QcFlag | None = None
        self._comment_category: str = ""
        self._comment: str = ""

    @property
    def selected_values(self) -> list[Parameter]:
        return self._selected_values

    @property
    def pending_flag(self) -> QcFlag | None:
        return self._pending_flag

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

    def request_flag(self, flag: QcFlag):
        self._pending_flag = flag
        self._notify_listeners(self.FLAG_REQUESTED)

    def confirm_flag(self, category: str, comment: str):
        if not self._selected_values:
            return
        self._comment_category = category
        self._comment = comment
        for value in self._selected_values:
            value.qc.manual = self._pending_flag
        self._notify_listeners(self.QC_PERFORMED)
        self._last_sender.select_values(self._parameter_index, self._value_index)
        self._pending_flag = None

    def cancel_flag(self):
        self._notify_listeners(self.FLAG_CANCELLED)
        self._pending_flag = None
