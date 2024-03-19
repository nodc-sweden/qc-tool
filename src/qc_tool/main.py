from pathlib import Path

import pandas as pd
from bokeh.layouts import layout
from bokeh.models import Div, Dropdown
from bokeh.plotting import curdoc, figure

from qc_tool.parameter_slot import ParameterSlot
from qc_tool.station import Station
from qc_tool.station_info import StationInfo


class QcTool:
    def __init__(self, data_path):
        self._stations = []
        self.parse_data(data_path)
        self._selected_station = None

        # Station
        self._station_dropdown = Dropdown(
            label="Select station", button_type="default", menu=self._stations
        )
        self._station_dropdown.on_click(self.select_new_station)

        self._station_info = StationInfo()

        # Map
        self._map = figure(
            x_range=(880000, 3000000),
            y_range=(7300000, 10000000),
            x_axis_type="mercator",
            y_axis_type="mercator",
            width=500,
        )
        self._map.add_tile("CARTODBPOSITRON")

        # Parameters
        first_parameter = ParameterSlot()
        self._parameters = [
            first_parameter,
            ParameterSlot(linked_y_range=first_parameter.y_range),
            ParameterSlot(linked_y_range=first_parameter.y_range),
        ]

        self.layout = layout(
            [
                [self._station_dropdown],
                [self._station_info.div, self._map],
                [parameter.get_layout() for parameter in self._parameters],
            ],
        )

        curdoc().title = "QC Tool"
        curdoc().add_root(self.layout)

    def select_new_station(self, event):
        station_name = event.item
        self._station_dropdown.label = station_name
        self._selected_station = Station(
            station_name,
            self._data.loc[station_name]
        )
        self._station_info.set_station(self._selected_station)

        for parameter in self._parameters:
            parameter.update_station(self._selected_station)

    def parse_data(self, data: pd.DataFrame):

        self._data = data.pivot_table(
            values="value",
            index=[
                "STNCODE",
                "DEPH",
                "COMNT_VISIT",
                "WADEP",
                "STATN",
                "WINDR",
                "WINSP",
                "AIRTEMP",
                "AIRPRES"
            ],
            columns="parameter",
        ).reset_index(level=list(range(2,9)))
        self._stations = list(self._data.index.get_level_values("STNCODE").unique())


def main():
    data_path = Path(
        "/home/k000840/code/oceanografi/qc-tool/test_data/"
        "2024-03-14_1559-2023-LANDSKOD_77-FARTYGSKOD_10_row_format_utf8.txt"
    )
    data = dataframe = pd.read_csv(data_path, sep="\t")
    QcTool(data)


main()
