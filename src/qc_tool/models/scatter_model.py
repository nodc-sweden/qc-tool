from qc_tool.models.base_model import BaseModel


class ScatterModel(BaseModel):
    NEW_SELECTION = "NEW_SELECTION"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_scatter_index = None

    @property
    def selected_scatter_index(self):
        return self._selected_scatter_index

    @selected_scatter_index.setter
    def selected_scatter_index(self, selected_scatter_index: int):
        self._selected_scatter_index = selected_scatter_index
        self._notify_listeners(self.NEW_SELECTION)
