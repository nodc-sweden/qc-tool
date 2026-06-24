from qc_tool.models.base_model import BaseModel


class CtdFileModel(BaseModel):
    NEW_DATA = "NEW_DATA"
    LOAD_ABORTED = "LOAD_ABORTED"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = None
        self._file_paths = []

    @property
    def data(self):
        return self._data

    @property
    def file_paths(self):
        return self._file_paths

    def add_data(self, data, file_path):
        self._data = data
        self._file_paths = [file_path]
        self._notify_listeners(self.NEW_DATA)

    def no_new_data(self):
        self._notify_listeners(self.LOAD_ABORTED)

    def clear_data(self):
        self._data = None
        self._file_paths = []
