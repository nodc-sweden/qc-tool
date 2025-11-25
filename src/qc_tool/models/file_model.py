from pathlib import Path

from qc_tool.models.base_model import BaseModel


class FileModel(BaseModel):
    NEW_DATA = "NEW_DATA"
    LOAD_ABORTED = "LOAD_ABORTED"
    UPDATED_DATA = "UPDATED_DATA"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_path = None
        self._data = None
        self._validation = None

    def no_new_data(self):
        self._notify_listeners(self.LOAD_ABORTED)

    def add_data(self, data, file_path: Path):
        self._data = data
        self._file_path = file_path
        self._notify_listeners(self.NEW_DATA)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, new_data):
        self._data = new_data
        self._notify_listeners(self.NEW_DATA)

    @property
    def file_path(self):
        return self._file_path

    def data_flags_update(self, new_data):
        self._data = new_data
        self._notify_listeners(self.UPDATED_DATA)
