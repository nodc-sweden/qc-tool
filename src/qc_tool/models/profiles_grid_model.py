from qc_tool.models.base_model import BaseModel


class ProfileGridModel(BaseModel):
    NEW_GRID_SIZE = "NEW_GRID_SIZE"

    def __init__(self, rows=2, columns=3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._columns = columns
        self._rows = rows

    @property
    def number_of_profiles(self):
        return self._columns * self._rows

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, columns):
        self._columns = columns
        self._notify_listeners(self.NEW_GRID_SIZE)

    @property
    def rows(self):
        return self._rows

    @rows.setter
    def rows(self, rows):
        self._rows = rows
        self._notify_listeners(self.NEW_GRID_SIZE)
