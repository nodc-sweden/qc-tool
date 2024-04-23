import pandas as pd
from bokeh.layouts import layout
from bokeh.models import Column, Tabs, TabPanel, Row
from bokeh.plotting import curdoc

from qc_tool.file_handler import FileHandler
from qc_tool.flag_info import FlagInfo
from qc_tool.map import Map
from qc_tool.profile_slot import ProfileSlot
from qc_tool.scatter_slot import ScatterSlot
from qc_tool.static.station_navigator import StationNavigator
from qc_tool.station import Station
from qc_tool.station_info import StationInfo


class QcTool:
    def __init__(self):
        self._data = None
        self._stations = {}
        self._selected_station = None

        self._station_navigator = StationNavigator(self.set_station)
        self._station_info = StationInfo()
        self._map = Map(self.set_station)

        # Parameters
        first_parameter = ProfileSlot(parameter="DOXY_BTL")
        self._profile_parameters = [
            first_parameter,
            ProfileSlot(linked_parameter=first_parameter, parameter="PHOS"),
            ProfileSlot(linked_parameter=first_parameter, parameter="NTRZ"),
            ]
        self._scatter_parameters = [
            ScatterSlot(x_parameter="DOXY_BTL", y_parameter="DOXY_CTD"),
            ScatterSlot(x_parameter="ALKY", y_parameter="SALT_CTD"),
            ScatterSlot(x_parameter="PHOS", y_parameter="NTRZ")
            ]

        self._file_handler = FileHandler(self.load_file_callback)
        self._flag_info = FlagInfo()

        self.layout = layout(
            [
                [
                    self._map.layout,
                    Column(self._station_navigator.layout, self._station_info.layout),
                    Tabs(
                        tabs=[
                            TabPanel(title="Files", child=self._file_handler.layout),
                            TabPanel(title="QC Flags", child=self._flag_info.layout),
                        ]
                    ),
                ],
                [Tabs(
                    tabs=[TabPanel(
                        child=Row(
                            children=[parameter.layout for parameter in self._profile_parameters]
                        ), title='profiles'
                    ),
                    TabPanel(
                        child=Row(
                            children=[parameter.layout for parameter in self._scatter_parameters]
                        ), title='scatter'
                    )]
                )],
            ],
        )
        
        curdoc().title = "QC Tool"
        curdoc().add_root(self.layout)

    def load_file_callback(self, data):
        self._parse_data(data)

    def set_station(self, station_series: str):
        self._station_navigator.set_station(station_series)
        self._selected_station = self._stations[station_series]
        self._station_info.set_station(self._selected_station)
        self._map.set_station(self._selected_station.series)
        for parameter in self._profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._scatter_parameters:
            parameter.update_station(self._selected_station)

    def _parse_data(self, data: pd.DataFrame):
        data["SERNO"] = data["SERNO"].map("{:03}".format)
        self._data = data

        station_series = sorted(self._data["SERNO"].unique())
        self._stations = {
            series: Station(series, self._data[self._data["SERNO"] == series])
            for series in station_series
        }

        self._station_navigator.load_stations(self._stations)
        self._map.load_stations(self._stations)
        self.set_station(station_series[0])


QcTool()
