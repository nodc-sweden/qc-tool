from qc_tool.models.base_model import BaseModel


class ManualQcModel(BaseModel):
    VALUES_SELECTED = "VALUES_SELECTED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_values = []

    @property
    def selected_values(self):
        return self._selected_values

    @selected_values.setter
    def selected_values(self, values):
        self._selected_values = values
        self._notify_listeners(self.VALUES_SELECTED)
