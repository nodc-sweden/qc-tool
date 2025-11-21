import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.map_controller import MapController

from bokeh.models import (
    PanTool,
    ResetTool,
    TapTool,
    WheelZoomTool,
)
from bokeh.plotting import figure

from qc_tool.models.map_model import MapModel
from qc_tool.views.base_view import BaseView


class MapView(BaseView):
    default_x_range = (0, 3_812_500)
    default_y_range = (6_950_000, 10_000_000)

    def __init__(
        self, controller: "MapController", map_model: MapModel, width=500, height=400
    ):
        self._controller = controller
        self._controller.map_view = self

        self._map_model = map_model

        tap = TapTool(mode="replace")
        wheel_zoom = WheelZoomTool(zoom_on_axis=False)

        self._stations = {}
        self._map = figure(
            x_axis_type="mercator",
            y_axis_type="mercator",
            x_range=self.default_x_range,
            y_range=self.default_y_range,
            width=width,
            height=height,
            tools=[PanTool(), tap, wheel_zoom, ResetTool()],
            match_aspect=True,
        )
        self._map.toolbar.active_scroll = wheel_zoom
        self._map.add_tile("Esri.OceanBasemap")

        self._map.scatter(
            x="longitudes",
            y="latitudes",
            source=self._map_model.unselected,
            line_width=0,
            fill_alpha=0.7,
            nonselection_fill_alpha=0.7,
            selection_fill_alpha=0.7,
            size=9,
            fill_color="blue",
            nonselection_fill_color="blue",
            selection_fill_color="orange",
        )

        self._map_model.unselected.selected.on_change(
            "indices", self._station_selected_callback
        )

    @property
    def height(self):
        return self._map.height

    @property
    def width(self):
        return self._map.width

    @property
    def layout(self):
        return self._map

    def _station_selected_callback(self, attr, old, new):
        if new:
            selected_index = new[0]
            station_visit = self._map_model.unselected.data["visit_keys"][selected_index]
            self._controller.select_visit(station_visit)

    def set_position(self, x_start, x_end, y_start, y_end):
        self._map.x_range.start = x_start
        self._map.x_range.end = x_end
        self._map.y_range.start = y_start
        self._map.y_range.end = y_end

    def reset_map(self):
        self.set_position(*self.default_x_range, *self.default_y_range)
