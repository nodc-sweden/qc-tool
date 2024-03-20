from pathlib import Path

import pandas as pd
from bokeh.layouts import layout
from bokeh.models import Dropdown
from bokeh.plotting import curdoc
from qc_tool.map import Map

from qc_tool.parameter_slot import ParameterSlot
from qc_tool.station import Station
from qc_tool.station_info import StationInfo


class QcTool:
    def __init__(self, data):
        self._data = None
        self._stations = {}
        self.parse_data(data)
        self._selected_station = None

        # Station
        self._station_dropdown = Dropdown(
            label="Select station",
            button_type="default",
            menu=list(map(str, self._stations.keys())),
        )
        self._station_dropdown.on_click(self.station_dropdown_callback)

        self._station_info = StationInfo()
        self._map = Map(self._stations, self.set_station)

        # Parameters
        first_parameter = ParameterSlot(default_parameter="DOXY_BTL")
        self._parameters = [
            first_parameter,
            ParameterSlot(linked_y_range=first_parameter.y_range, default_parameter="PHOS"),
            ParameterSlot(linked_y_range=first_parameter.y_range, default_parameter="NTRZ"),
        ]

        self.layout = layout(
            [
                [self._station_dropdown],
                [self._map.layout, self._station_info.div],
                [parameter.get_layout() for parameter in self._parameters],

            ],
        )

        curdoc().title = "QC Tool"
        curdoc().add_root(self.layout)

    def set_station(self, station_id):
        self._station_dropdown.label = station_id
        self._selected_station = Station(station_id, self._data.loc[station_id])
        self._station_info.set_station(self._selected_station)
        self._map.set_station(self._selected_station.name)
        for parameter in self._parameters:
            parameter.update_station(self._selected_station)

    def station_dropdown_callback(self, event):
        station_id = event.item
        self.set_station(station_id)

    def parse_data(self, data: pd.DataFrame):
        data['STNNO'] = data['STNNO'].astype(str)
        data = data.pivot_table(
            values="value",
            index=[
                "STNNO",
                "DEPH",
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
        ).reset_index(level=list(range(2, 15)))

        self._data = data

        self._stations = {
            station_id: Station(station_id, self._data.loc[station_id])
            for station_id in self._data.index.get_level_values("STNNO").unique()
        }


def main():
    data_path = Path(
        "/home/k000840/code/oceanografi/qc-tool/test_data/"
        "2024-03-19_1656-2024-LANDSKOD_77-FARTYGSKOD_10_row_format.txt"
    )

    data = pd.read_csv(data_path, sep="\t")
    QcTool(data)


main()
