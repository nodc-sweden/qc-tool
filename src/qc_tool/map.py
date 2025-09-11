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
            x_range=(700000, 2500000),
            y_range=(7000000, 8500000),
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

    def set_station(self, station_visit: Optional[str]):
        """
        This method is used to change the selected station on the map from main.py
        This is for example called if station is selected from the station_navigator
        """
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
                # this calls the set_station in main.py
                self._set_station_callback(station_visit)

    def _convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes


class MultiStationMap(Layoutable):
    def __init__(self, set_station_callback):
        """
        User clicks a station on the map:
        1. ColumnDataSource.selected.indices changes.
        2. _station_selected_callback is called.
        3. It looks up which stations are selected (selected_visits).
        4. It calls _set_station_callback(selected_visits)
            → this calls main.py's update_selected_stations(selected_stations).
        5. In main.py's update_selected_stations, you might call
            multimap.set_stations(selected_stations) again
            (to update the map programmatically if needed).
        """
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

        self.set_map_stations(None)

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

    def set_map_stations(self, station_visits):
        """
        Takes a list of station objects (station_visits) and updates the map selection.
        This method is used to change the selected station on the map from main.py
        This is for example called if station is selected from the station_navigator
        """
        print(station_visits)

        # station_index = self._map_unselected_source.data["visits"].index(station_visit)
        if station_visits:
            station_indeces = [
                self._map_unselected_source.data["visits"].index(station_visit)
                for station_visit in station_visits
            ]
            self._map_unselected_source.selected.indices = station_indeces
        else:
            self._map_unselected_source.selected.indices = []

    @property
    def layout(self):
        return self._map

    def _station_selected_callback(self, attr, old, new):
        """
        This is the callback from clicking in the map
        """
        if new:
            # Get all selected visits
            selected_visits = [self._map_unselected_source.data["visits"][i] for i in new]
            print(
                f"print selected visits when clicking map and send to callback in main.py: \n{selected_visits}"  # noqa: E501
            )
            # Pass list of Station objects instead of a single station
            # this calls the update_selected_stations() in main.py
            self._set_station_callback(selected_visits)
        else:
            self._set_station_callback([])

        # station_visit = self._map_unselected_source.data["visits"][selected_index]
        # if station_visit != self._selected_station:
        #     # this calls the set_station in main.py
        #     self._set_station_callback(station_visit)

    def _convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes
