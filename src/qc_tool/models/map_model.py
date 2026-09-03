from bokeh.models.sources import ColumnDataSource

from qc_tool.models.base_model import BaseModel


class MapModel(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_source = ColumnDataSource(
            data={
                "latitudes": [],
                "longitudes": [],
                "visit_keys": [],
                "color": [],
                "status": [],
            },
        )

    def set_points(self, points):
        self._data_source.data = points

    def set_selection(self, visit_keys: list[str]):
        new_indices = [
            self._data_source.data["visit_keys"].index(key) for key in visit_keys
        ]
        # only update if indices differ
        if self._data_source.selected.indices != new_indices:
            self._data_source.selected.indices = new_indices

    @property
    def unselected(self):
        return self._data_source
