from bokeh.models import PanTool, ResetTool, TapTool, WheelZoomTool, ColumnDataSource, \
    Circle, Scatter
from bokeh.plotting import figure
from pyproj import Transformer


class Map:
    def __init__(self, stations, set_station_callback):
        self._set_station_callback = set_station_callback
        self._transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")

        tap = TapTool()
        wheel_zoom = WheelZoomTool(zoom_on_axis=False)

        self._stations = stations
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

        longitudes = [station.longitude for station in self._stations.values()]
        latitudes = [station.latitude for station in self._stations.values()]
        longitudes, latitudes = self.convert_projection(longitudes, latitudes)
        self._map_source = ColumnDataSource(
            data={"latitudes": latitudes, "longitudes": longitudes},
        )

        renderer = self._map.scatter(
            x="longitudes",
            y="latitudes",
            source=self._map_source,
            size=7,
            selection_fill_alpha=0.8,
            selection_fill_color="red",
            nonselection_fill_alpha=0.8,
            nonselection_fill_color="blue",
        )

        #renderer.selection_glyph = Scatter(fill_alpha=0.8, fill_color="red", size=9)
        #renderer.nonselection_glyph = Scatter(fill_alpha=0.8, fill_color="blue", size=7)

        self._map_source.selected.on_change("indices", self.callback)
        self.set_station("")

    def set_station(self, station_id: str):
        unselected_locations = [
            (station.name, station.longitude, station.latitude)
            for station in self._stations.values()
        ]

        unselected_names, unselected_longitudes, unselected_latitudes = (
            zip(*unselected_locations) if unselected_locations else ((), (), ())
        )

        unselected_longitudes, unselected_latitudes = self.convert_projection(
            unselected_longitudes, unselected_latitudes
        )

        self._map_source.data = {
            "longitudes": unselected_longitudes,
            "latitudes": unselected_latitudes,
            "names": unselected_names,
        }

    @property
    def layout(self):
        return self._map

    def callback(self, attr, old, new):
        if new:
            selection = new[0]
            station_id = self._map_source.data["names"][selection]
            self._set_station_callback(station_id)

    def convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes
