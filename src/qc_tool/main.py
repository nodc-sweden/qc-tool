import pandas as pd
from bokeh.layouts import layout
from bokeh.models import Column
from bokeh.plotting import curdoc

from qc_tool.file_handler import FileHandler
from qc_tool.map import Map
from qc_tool.parameter_slot import ParameterSlot
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
        first_parameter = ParameterSlot(parameter="DOXY_BTL")
        self._parameters = [
            first_parameter,
            ParameterSlot(linked_parameter=first_parameter, parameter="PHOS"),
            ParameterSlot(linked_parameter=first_parameter, parameter="NTRZ"),
        ]

        self._file_handler = FileHandler(self.load_file_callback)

        self.layout = layout(
            [
                [
                    self._map.layout,
                    Column(self._station_navigator.layout, self._station_info.layout),
                    self._file_handler.layout,
                ],
                [parameter.layout for parameter in self._parameters],
            ],
        )

        curdoc().title = "QC Tool"
        curdoc().add_root(self.layout)

    def load_file_callback(self, data):
        self._parse_data(data)

    def set_station(self, station_series: str):
        self._station_navigator.set_station(station_series)
        self._selected_station = Station(station_series, self._data.loc[station_series])
        self._station_info.set_station(self._selected_station)
        self._map.set_station(self._selected_station.series)
        for parameter in self._parameters:
            parameter.update_station(self._selected_station)

    def _parse_data(self, data: pd.DataFrame):
        data["STNNO"] = data["STNNO"].map("{:03}".format)
        data = (
            data.pivot_table(
                values="value",
                index=[
                    "STNNO",
                    "DEPH",
                    "STATN",
                    "SDATE",
                    "STIME",
                    "CTRYID",
                    "SHIPC",
                    "CRUISE_NO",
                    "COMNT_VISIT",
                    "WADEP",
                    "WINDR",
                    "WINSP",
                    "AIRTEMP",
                    "AIRPRES",
                    "LATIT",
                    "LONGI",
                ],
                columns="parameter",
            )
            .reset_index(level=list(range(2, 16)))
            .sort_values(["STNNO", "DEPH"])
        )
        self._data = data
        station_series = sorted(self._data.index.get_level_values("STNNO").unique())

        self._stations = {
            series: Station(series, self._data.loc[series]) for series in station_series
        }

        self._station_navigator.load_stations(self._stations)
        self._map.load_stations(self._stations)
        self.set_station(station_series[0])


QcTool()
