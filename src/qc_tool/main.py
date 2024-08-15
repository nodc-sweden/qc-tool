import time

import pandas as pd
from bokeh.models import Column, Row, TabPanel, Tabs
from bokeh.plotting import curdoc
from fyskemqc.fyskemqc import FysKemQc
from fyskemqc.qc_flag_tuple import QcField

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
        first_parameter = ProfileSlot(parameter="PHOS")
        first_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._chemical_profile_parameters = [
            first_parameter,
            ProfileSlot(linked_parameter=first_parameter, parameter="NTRI"),
            ProfileSlot(linked_parameter=first_parameter, parameter="NTRA"),
            ProfileSlot(linked_parameter=first_parameter, parameter="AMON"),
            ProfileSlot(linked_parameter=first_parameter, parameter="SIO3-SI"),]
        first_parameter = ProfileSlot(parameter="SALT_CTD")
        first_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._physical_profile_parameters = [
            first_parameter,
            ProfileSlot(linked_parameter=first_parameter, parameter="TEMP_CTD"),
            ProfileSlot(linked_parameter=first_parameter, parameter="DOXY_CTD"),
            ProfileSlot(linked_parameter=first_parameter, parameter="DOXY_BTL"),
            ProfileSlot(linked_parameter=first_parameter, parameter="H2S"),]

        self._scatter_parameters = [
            ScatterSlot(x_parameter="DOXY_BTL", y_parameter="DOXY_CTD"),
            ScatterSlot(x_parameter="ALKY", y_parameter="SALT_CTD"),
            ScatterSlot(x_parameter="PHOS", y_parameter="NTRZ"),
            ScatterSlot(x_parameter="H2S", y_parameter="NTRZ"),
        ]

        self._file_handler = FileHandler(
            self.load_file_callback, self.automatic_qc_callback
        )
        self._flag_info = FlagInfo()

        # Top row
        station_info_column = Column(
            self._station_navigator.layout, self._station_info.layout
        )
        files_tab = TabPanel(title="Files", child=self._file_handler.layout)
        flags_tab = TabPanel(title="QC Flags", child=self._flag_info.layout)
        extra_info_tabs = Tabs(tabs=[files_tab, flags_tab])
        top_row = Row(self._map.layout, station_info_column, extra_info_tabs)

        # Bottom row

        # Profiles tab
        profile_row1 = Row(
                children=[parameter.layout for parameter in self._chemical_profile_parameters]
            )
        profile_row2 = Row(
                children=[parameter.layout for parameter in self._physical_profile_parameters]
            )
        profile_column = Column(profile_row1, profile_row2)
        profile_tab = TabPanel(
            child=profile_column,
            title="profiles",
        )

        # Scatter tab
        scatter_tab = TabPanel(
            child=Row(
                children=[parameter.layout for parameter in self._scatter_parameters]
            ),
            title="scatter",
        )
        bottom_row = Row(Tabs(tabs=[profile_tab, scatter_tab]))

        # Full layout
        self.layout = Column(top_row, bottom_row)
        curdoc().title = "QC Tool"
        curdoc().add_root(self.layout)

    def load_file_callback(self, data):
        self._parse_data(data)

    def automatic_qc_callback(self):
        print("Automatic QC started...")
        t0 = time.perf_counter()
        fys_kem_qc = FysKemQc(self._data)
        fys_kem_qc.run_automatic_qc()
        t1 = time.perf_counter()
        print(f"Automatic QC finished ({t1-t0:.3f} .s)")
        self._parse_data(self._data, self._selected_station.series)

    def set_station(self, station_series: str):
        self._station_navigator.set_station(station_series)
        self._selected_station = self._stations[station_series]
        self._station_info.set_station(self._selected_station)
        self._map.set_station(self._selected_station.series)
        for parameter in self._physical_profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._chemical_profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._scatter_parameters:
            parameter.update_station(self._selected_station)

    def _parse_data(self, data: pd.DataFrame, station: str = None):
        # Create station name with zero padded serial number
        data["SERNO"] = data["SERNO"].map("{:03}".format)
        data["SERNO_STN"] = data["SERNO"] + " - " + data["STATN"]

        # Create the long qc string using "quality_flag" as incoming qc
        if "quality_flag_long" not in data.columns and "quality_flag" in data.columns:
            data["quality_flag_long"] = data["quality_flag"] + f"_{'0' * len(QcField)}_0"

        self._data = data

        # Extract list of all station visits
        station_series = sorted(data["SERNO_STN"].unique())

        # Initialize all stations
        self._stations = {
            series: Station(series, self._data[self._data["SERNO_STN"] == series])
            for series in station_series
        }

        self._station_navigator.load_stations(self._stations)
        self._map.load_stations(self._stations)
        self.set_station(station or station_series[0])


QcTool()
