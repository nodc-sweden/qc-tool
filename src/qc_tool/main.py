import pandas as pd
from bokeh.models import Column, Row, TabPanel, Tabs
from bokeh.plotting import curdoc
from fyskemqc.fyskemqc import FysKemQc
from fyskemqc.qc_flags import QcFlags
from fyskemqc.qc_flag import QcFlag

from metadataqc.metadataqc import MetaDataQc

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
        first_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._profile_parameters = [
            first_parameter,
            ProfileSlot(linked_parameter=first_parameter, parameter="PHOS"),
            ProfileSlot(linked_parameter=first_parameter, parameter="NTRZ"),
            ProfileSlot(linked_parameter=first_parameter, parameter="AMON"),
            ProfileSlot(linked_parameter=first_parameter, parameter="SALT_CTD"),
        ]
        self._scatter_parameters = [
            ScatterSlot(x_parameter="DOXY_BTL", y_parameter="DOXY_CTD"),
            ScatterSlot(x_parameter="ALKY", y_parameter="SALT_CTD"),
            ScatterSlot(x_parameter="PHOS", y_parameter="NTRZ"),
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
        profile_tab = TabPanel(
            child=Row(
                children=[parameter.layout for parameter in self._profile_parameters]
            ),
            title="profiles",
        )
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
        self._metadata_check()
        # lägg till metadata test här

    def automatic_qc_callback(self):
        """
        Kör automatisk qc på en station i taget.
        self._stations har skapats första gången _parse_data har körts
        """

        print("Nu börjas det")
        for series, station in self._stations.items():
            fys_kem_qc = FysKemQc(self._data.loc[station.indices])
            fys_kem_qc.run_automatic_qc()
            # Uppdatera orginalet (self._data) med de nya värdena
            for index, new_value in fys_kem_qc.updates.items():
                self._data.loc[index, 'quality_flag_long'] = new_value

        print(f"unika quality_flag_long: {self._data['quality_flag_long'].unique()}")
        self._parse_data(self._data)
        print("KLART!")


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
        data["SERNO_STN"] = data["SERNO"] + " - " + data["STATN"]

        # Lägg til quality_flag_long som innehåller incoming_automatic_manual.
        if "quality_flag_long" not in data:
            try:
                data["quality_flag_long"] = data["quality_flag"].map(
                    lambda x: str(QcFlags(QcFlag.parse(x), None, None))
                )
            except Exception:
                print('tried to set quality_flag_long')
                raise

        self._data = data

        station_series = sorted(data["SERNO_STN"].unique())
        # en dict med stationsobjekt, nyckel stationens serie
        self._stations = {
            series: Station(series, self._data[self._data["SERNO_STN"] == series])
            for series in station_series
        }

        self._station_navigator.load_stations(self._stations)
        self._map.load_stations(self._stations)
        self.set_station(station_series[0])

    def _metadata_check(self):
        print("kollar metadata")
        print("de här serierna finns:")
        for serie, station in self._stations.items():
            print(serie)
            meta_data_qc = MetaDataQc(station.common)
            meta_data_qc.run_automatic_qc()
            print(meta_data_qc.report)


QcTool()
