from pathlib import Path

import polars as pl

from qc_tool.models.base_model import BaseModel


class FileModel(BaseModel):
    NEW_DATA = "NEW_DATA"
    LOAD_ABORTED = "LOAD_ABORTED"
    UPDATED_DATA = "UPDATED_DATA"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_paths = []
        self._data = None
        self._validation = None

    def no_new_data(self):
        self._notify_listeners(self.LOAD_ABORTED)

    def add_data(self, data, file_path: Path, add_to_existing: bool = False):
        if add_to_existing and self._data is not None:
            self._data = pl.concat([self._data, data])
            self._file_paths.append(file_path)
        else:
            self._data = data
            self._file_paths = [file_path]
        self._notify_listeners(self.NEW_DATA)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, new_data):
        self._data = new_data
        self._notify_listeners(self.NEW_DATA)

    @property
    def file_paths(self):
        return self._file_paths

    def data_flags_update(self, new_data):
        self._data = new_data
        self._notify_listeners(self.UPDATED_DATA)
