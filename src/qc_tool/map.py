from typing import Optional

from bokeh.models import (
    ColumnDataSource,
    PanTool,
    ResetTool,
    TapTool,
    WheelZoomTool,
)
from bokeh.plotting import figure
from pyproj import Transformer

from qc_tool.layoutable import Layoutable


class Map(Layoutable):
    def __init__(self, set_station_callback):
        self._set_station_callback = set_station_callback
        self._transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")
        self._selected_station = None

        tap = TapTool(mode="replace")
        wheel_zoom = WheelZoomTool(zoom_on_axis=False)

        self._stations = {}
        self._map = figure(
            x_axis_type="mercator",
            y_axis_type="mercator",
            x_range=(0, 3_812_500),
            y_range=(6_950_000, 10_000_000),
            width=500,
            height=400,
            tools=[PanTool(), tap, wheel_zoom, ResetTool()],
            match_aspect=True,
        )
        self._map.toolbar.active_scroll = wheel_zoom
        self._map.add_tile("Esri.OceanBasemap")

        self._map_unselected_source = ColumnDataSource(
            data={"latitudes": [], "longitudes": [], "series": []},
        )
        self._map_selected_source = ColumnDataSource(
            data={"latitudes": [], "longitudes": [], "series": []},
        )

        self._map.scatter(
            x="longitudes",
            y="latitudes",
            source=self._map_unselected_source,
            line_width=0,
            fill_alpha=0.7,
            nonselection_fill_alpha=0.7,
            selection_fill_alpha=0.7,
            size=9,
            fill_color="blue",
            nonselection_fill_color="blue",
            selection_fill_color="orange",
        )

        self._map_unselected_source.selected.on_change(
            "indices", self._station_selected_callback
        )

        self.set_station(None)

    def load_stations(self, stations):
        self._stations = stations

        all_stations = [
            (station.visit_key, station.longitude, station.latitude)
            for station in self._stations.values()
        ]

        station_names, longitudes, latitudes = zip(*all_stations)
        longitudes, latitudes = self._convert_projection(longitudes, latitudes)

        self._map_unselected_source.data = {
            "longitudes": longitudes,
            "latitudes": latitudes,
            "visits": station_names,
        }

        self.zoom_to_points()

    def zoom_to_points(self):
        margin_ratio = 1.25
        x_min = min(self._map_unselected_source.data["longitudes"])
        x_max = max(self._map_unselected_source.data["longitudes"])
        y_min = min(self._map_unselected_source.data["latitudes"])
        y_max = max(self._map_unselected_source.data["latitudes"])

        data_width = (x_max - x_min) * margin_ratio
        data_height = (y_max - y_min) * margin_ratio

        center_x = (x_max + x_min) / 2
        center_y = (y_max + y_min) / 2

        plot_ratio = self._map.width / self._map.height
        data_ratio = data_width / data_height

        if data_ratio > plot_ratio:
            data_height = data_width / plot_ratio
        else:
            data_width = data_height * plot_ratio

        self._map.x_range.start = center_x - data_width / 2
        self._map.x_range.end = center_x + data_width / 2
        self._map.y_range.start = center_y - data_height / 2
        self._map.y_range.end = center_y + data_height / 2

    def set_station(self, station_visit: Optional[str]):
        self._selected_station = station_visit
        if station_visit:
            station_index = self._map_unselected_source.data["visits"].index(
                station_visit
            )
            self._map_unselected_source.selected.indices = [station_index]
        else:
            self._map_unselected_source.selected.indices = []

    @property
    def layout(self):
        return self._map

    def _station_selected_callback(self, attr, old, new):
        if new:
            selected_index = new[0]
            station_visit = self._map_unselected_source.data["visits"][selected_index]
            if station_visit != self._selected_station:
                self._set_station_callback(station_visit)

    def _convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes
