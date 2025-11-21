from bokeh.models.sources import ColumnDataSource

from qc_tool.models.base_model import BaseModel


class MapModel(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_source = ColumnDataSource(
            data={"latitudes": [], "longitudes": [], "visit_keys": []},
        )

    def set_points(self, points):
        self._data_source.data = points

    def set_selection(self, visit_keys: list[str]):
        self._data_source.selected.indices = [
            self._data_source.data["visit_keys"].index(key) for key in visit_keys
        ]

    @property
    def unselected(self):
        return self._data_source

    @property
    def selected(self):
        return self._selected_data_source
