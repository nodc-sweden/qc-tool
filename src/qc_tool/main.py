import csv
import time
from functools import partial
from pathlib import Path
from random import random
from threading import Thread

import numpy as np
import pandas as pd
from bokeh.layouts import layout, column
from bokeh.models import ColumnDataSource, Div, Button, CustomJS, Dropdown
from bokeh.plotting import curdoc, figure, show
from bokeh.tile_providers import CARTODBPOSITRON, get_provider


class QcTool:
    def __init__(self, data_path):
        self._stations = []
        self.parse_data(data_path)
        self._selected_station = None

        self._header = Div(text="<h1>Select station</h1>")

        # Station
        self.station_dropdown = Dropdown(
            label="Station", button_type="default", menu=self._stations
        )
        self.station_dropdown.on_click(self.select_new_station)

        # Map

        tile_provider = get_provider(CARTODBPOSITRON)
        # range bounds supplied in web mercator coordinates
        self._map = figure(x_range=(-2000000, 6000000), y_range=(-1000000, 7000000),
                   x_axis_type="mercator", y_axis_type="mercator")
        self._map.add_tile(tile_provider)

        # Parameters
        first_parameter = ParameterSlot()
        self._parameters = [
            first_parameter,
            ParameterSlot(linked_y_range=first_parameter.y_range),
            ParameterSlot(linked_y_range=first_parameter.y_range),
        ]

        self.layout = layout(
            [
                [self._header, self.station_dropdown],
                [self._map],
                [parameter.get_layout() for parameter in self._parameters],
            ]
        )

        curdoc().title = "QC Tool"
        curdoc().add_root(self.layout)

    def select_new_station(self, event):
        station_name = event.item
        self._header.text = f"<h1>{station_name}</h1>"
        self._selected_station = Station(
            station_name,
            self._data.loc[station_name]
        )

        for parameter in self._parameters:
            parameter.update_station(self._selected_station)

    def parse_data(self, data_path: Path):
        dataframe = pd.read_csv(data_path, sep="\t")
        self._data = dataframe[["STNCODE", "DEPH", "parameter", "value"]].pivot_table(
            "value", ["STNCODE", "DEPH"], "parameter"
        )
        self._stations = list(self._data.index.get_level_values("STNCODE").unique())


class Station:
    def __init__(self, name: str, data):
        self._name = name
        self._data = data
        self._parameters = list(data.dropna(axis=1, how="all").columns)

    @property
    def parameters(self) -> list[str]:
        return self._parameters

    @property
    def data(self):
        return self._data


class ParameterSlot:
    def __init__(
        self,
        title: str = None,
        parameter: str = None,
        station: Station = None,
        linked_y_range=None,
    ):
        self._title = title
        self._station = station
        self._parameter = parameter
        self._source = ColumnDataSource()
        self._figure_config = {"height": 500, "width": 500}
        self._plot_config = {"size": 7, "color": "navy", "alpha": 0.8}

        self._figure = figure(**self._figure_config)
        self._figure.circle("x", "y", source=self._source, **self._plot_config)
        if linked_y_range:
            self._figure.y_range = linked_y_range
        else:
            self._figure.y_range.flipped = True

        self._parameter_dropdown = Dropdown(
            label="Parameter",
            button_type="default",
            menu=self._station.parameters if station else [],
            name="Parameter",
        )

        self._parameter_dropdown.on_click(self.change_parameter)

    def update_station(self, station: Station):
        self._station = station
        self._parameter_dropdown.menu = self._station.parameters

        y = self._station.data.index
        if self._parameter in self._station.parameters:
            x = self._station.data[self._parameter]
        else:
            x = [np.nan] * len(y)

        self._source.data = {"x": x, "y": y}


    def change_parameter(self, event):
        self._parameter = event.item
        self._figure.title.text = self._parameter
        self._source.data["x"] = self._station.data[self._parameter]

    def get_layout(self):
        return column(
            self._figure,
            self._parameter_dropdown,
        )

    @property
    def y_range(self):
        return self._figure.y_range

def main():
    data_path = Path(
        "/home/k000840/code/oceanografi/qc-tool/test_data/"
        "2024-03-14_1559-2023-LANDSKOD_77-FARTYGSKOD_10_row_format.txt"
    )
    QcTool(data_path)


main()
