from bokeh.models import Button, Dropdown, Row

from qc_tool.layoutable import Layoutable


class StationNavigator(Layoutable):
    def __init__(self, set_station_callback):
        self._stations = None
        self._set_station_callback = set_station_callback

        self._previous_button = Button(label="<")
        self._previous_button.on_event("button_click", self.select_previous_station)

        self._next_button = Button(label=">")
        self._next_button.on_event("button_click", self.select_next_station)

        self._station_dropdown = Dropdown(
            label="Select station",
            button_type="default",
            min_width=250,
            max_width=400,
        )
        self._station_dropdown.on_click(self._select_station_callback)
        self._layout = Row(
            self._previous_button,
            self._station_dropdown,
            self._next_button,
            width=400,
        )

    def _select_station_callback(self, event):
        station_visit = event.item
        self._set_station_callback(station_visit)

    def select_previous_station(self):
        station_index = (
            self._station_dropdown.menu.index(self._station_dropdown.label) - 1
        ) % len(self._stations)
        station_visit = self._station_dropdown.menu[station_index]
        self._set_station_callback(station_visit)

    def select_next_station(self):
        station_index = (
            self._station_dropdown.menu.index(self._station_dropdown.label) + 1
        ) % len(self._stations)
        station_visit = self._station_dropdown.menu[station_index]
        self._set_station_callback(station_visit)

    def load_stations(self, stations):
        self._stations = stations
        self._station_dropdown.menu = [
            station.visit_key for station in self._stations.values()
        ]

    @property
    def layout(self):
        return self._layout

    def set_station(self, station_visit: str):
        self._station_dropdown.label = station_visit
