from bokeh.models import PanTool, ResetTool, TapTool, WheelZoomTool, ColumnDataSource
from bokeh.models.callbacks import CustomJS
from bokeh.plotting import figure
from pyproj import CRS, transform


class Map:
    def __init__(self, stations, set_station_callback):
        self._set_station_callback = set_station_callback

        tap = TapTool()
        wheel_zoom = WheelZoomTool()

        self._stations = stations
        self._map = figure(
            x_axis_type="mercator",
            y_axis_type="mercator",
            width=500,
            height=500,
            tools=[PanTool(), tap, wheel_zoom, ResetTool()],
            match_aspect=True,
        )
        self._map.toolbar.active_scroll = wheel_zoom
        self._map.add_tile("Esri.OceanBasemap")

        longitudes = [station.longitude for station in self._stations.values()]
        latitudes = [station.latitude for station in self._stations.values()]
        longitudes, latitudes = convert_projection(longitudes, latitudes)
        self._map_unselected_source = ColumnDataSource(
            data={"latitudes": latitudes, "longitudes": longitudes}
        )
        self._map_selected_source = ColumnDataSource(
            data={"latitudes": [], "longitudes": []}
        )

        self._map.circle(x="longitudes", y="latitudes", size=7, fill_color="blue",
                         fill_alpha=0.8, source=self._map_unselected_source)

        self._map.circle(x="longitudes", y="latitudes", size=9, fill_color="red",
                         fill_alpha=0.8, source=self._map_selected_source)

        self._map_unselected_source.selected.on_change("indices", self.callback)
        self.set_station("")

    def set_station(self, station_id: str):
        unselected_locations = [
            (station.name, station.longitude, station.latitude)
            for station in self._stations.values()
        ]

        unselected_names, unselected_longitudes, unselected_latitudes = zip(*unselected_locations) if unselected_locations else ((), (), ())

        unselected_longitudes, unselected_latitudes = convert_projection(
            unselected_longitudes, unselected_latitudes
        )

        self._map_unselected_source.data = {
            "longitudes": unselected_longitudes,
            "latitudes": unselected_latitudes,
            "names": unselected_names
        }

    @property
    def layout(self):
        return self._map

    def callback(self, attr, old, new):
        selection = new[0]
        station_id = self._map_unselected_source.data["names"][selection]
        self._set_station_callback(station_id)



def convert_projection(longitudes, latitudes):
    # TODO: https://pyproj4.github.io/pyproj/stable/gotchas.html#upgrading-to-pyproj-2-from-pyproj-1
    if not longitudes or not latitudes:
        return longitudes, latitudes

    project_projection = CRS('EPSG:4326')
    google_projection = CRS('EPSG:3857')
    transformed_longitudes, transformed_latitudes = transform(
        project_projection,
        google_projection,
        longitudes,
        latitudes,
        always_xy=True
    )
    return transformed_longitudes, transformed_latitudes
