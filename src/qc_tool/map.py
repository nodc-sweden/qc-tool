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


class Map:
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
            x_range=(700000, 2500000),
            y_range=(7000000, 8500000),
            width=500,
            height=300,
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
            selection_fill_color="red",
        )

        self._map_unselected_source.selected.on_change(
            "indices", self._station_selected_callback
        )

        self.set_station(None)

    def load_stations(self, stations):
        self._stations = stations

        all_stations = [
            (station.series, station.longitude, station.latitude)
            for station in self._stations.values()
        ]

        station_names, longitudes, latitudes = zip(*all_stations)
        longitudes, latitudes = self._convert_projection(longitudes, latitudes)

        self._map_unselected_source.data = {
            "longitudes": longitudes,
            "latitudes": latitudes,
            "series": station_names,
        }

    def set_station(self, station_series: Optional[str]):
        self._selected_station = station_series
        if station_series:
            station_index = self._map_unselected_source.data["series"].index(
                station_series
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
            station_series = self._map_unselected_source.data["series"][selected_index]
            if station_series != self._selected_station:
                self._set_station_callback(station_series)

    def _convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes
