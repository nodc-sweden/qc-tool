import os
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from bokeh.models import Column, Row, TabPanel, Tabs
from bokeh.plotting import curdoc
from nodc_statistics import regions
from ocean_data_qc.fyskemqc import FysKemQc

from qc_tool.data_transformation import prepare_data
from qc_tool.file_handler import FileHandler
from qc_tool.flag_info import FlagInfo
from qc_tool.map import Map
from qc_tool.profile_slot import ProfileSlot
from qc_tool.scatter_slot import ScatterSlot
from qc_tool.static.station_navigator import StationNavigator
from qc_tool.station import Station
from qc_tool.station_info import StationInfo

GEOLAYERS_AREATAG = {
    "typomrkust": "TYPOMRKUST",
    "Skagerrak_without_coast": "NAMN",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3": "level_34",
}


class QcTool:
    def __init__(self):
        self._data = None
        self._stations = {}
        self._selected_station = None

        self._station_navigator = StationNavigator(self.set_station)
        self._station_info = StationInfo()
        self._map = Map(self.set_station)

        # Parameters
        first_chemical_parameter = ProfileSlot(parameter="PHOS")
        first_chemical_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._chemical_profile_parameters = [
            first_chemical_parameter,
            ProfileSlot(linked_parameter=first_chemical_parameter, parameter="NTRI"),
            ProfileSlot(linked_parameter=first_chemical_parameter, parameter="NTRA"),
            ProfileSlot(linked_parameter=first_chemical_parameter, parameter="AMON"),
            ProfileSlot(linked_parameter=first_chemical_parameter, parameter="SIO3-SI"),
        ]

        first_physical_parameter = ProfileSlot(parameter="SALT_CTD")
        first_physical_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._physical_profile_parameters = [
            first_physical_parameter,
            ProfileSlot(linked_parameter=first_physical_parameter, parameter="TEMP_CTD"),
            ProfileSlot(linked_parameter=first_physical_parameter, parameter="DOXY_CTD"),
            ProfileSlot(linked_parameter=first_physical_parameter, parameter="DOXY_BTL"),
            ProfileSlot(linked_parameter=first_physical_parameter, parameter="H2S"),
        ]

        self._scatter_parameters = [
            ScatterSlot(x_parameter="DOXY_BTL", y_parameter="DOXY_CTD"),
            ScatterSlot(x_parameter="ALKY", y_parameter="SALT_CTD"),
            ScatterSlot(x_parameter="PHOS", y_parameter="NTRZ"),
            ScatterSlot(x_parameter="NTRZ", y_parameter="H2S"),
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

        # Tab for profile plots
        chemical_profile_row = Row(
            children=[parameter.layout for parameter in self._chemical_profile_parameters]
        )

        physical_profile_row = Row(
            children=[parameter.layout for parameter in self._physical_profile_parameters]
        )
        profile_tab = TabPanel(
            child=Column(chemical_profile_row, physical_profile_row), title="Profiles"
        )

        # Tab for scatter plots
        scatter_tab = TabPanel(
            child=Row(
                children=[parameter.layout for parameter in self._scatter_parameters]
            ),
            title="Scatter",
        )

        bottom_row = Row(Tabs(tabs=[profile_tab, scatter_tab]))

        # Full layout
        self.layout = Column(top_row, bottom_row)
        curdoc().title = "QC Tool"
        curdoc().add_root(self.layout)

    def load_file_callback(self, data):
        self._read_geo_info_file()
        data = self._match_sea_area(data)
        self._set_data(data)

    def automatic_qc_callback(self):
        print("Automatic QC started...")
        t0 = time.perf_counter()
        fys_kem_qc = FysKemQc(self._data)
        fys_kem_qc.run_automatic_qc()
        t1 = time.perf_counter()
        print(f"Automatic QC finished ({t1-t0:.3f} .s)")
        self._set_data(self._data, self._selected_station.series)

    def set_station(self, station_series: str):
        self._station_navigator.set_station(station_series)
        self._selected_station = self._stations[station_series]
        self._station_info.set_station(self._selected_station)
        self._map.set_station(self._selected_station.series)

        for parameter in self._chemical_profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._physical_profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._scatter_parameters:
            parameter.update_station(self._selected_station)

    def longitude(self, longi_dms):
        degrees, remainder = divmod(longi_dms, 100)
        return degrees + remainder / 60

    def latitude(self, latit_dms):
        degrees, remainder = divmod(latit_dms, 100)
        return degrees + remainder / 60

    def _match_sea_area(self, data):
        # Assuming df is your DataFrame and regions.sea_basin_for_position is the function
        # to apply

        # Step 1: Extract unique combinations of LONGI and LATIT
        unique_positions = data[["LONGI", "LATIT"]].drop_duplicates()
        # Step 2: Apply the function to each unique combination
        unique_positions["sea_basin"] = unique_positions.apply(
            lambda row: regions.sea_basin_for_position(
                self.longitude(row["LONGI"]), self.latitude(row["LATIT"]), self._geo_info
            ),
            axis=1,
        )
        # Step 3: Map the results back to the original DataFrame
        data = data.merge(unique_positions, on=["LONGI", "LATIT"], how="left")

        return data

    def _set_data(self, data: pd.DataFrame, station: str = None):
        self._data = prepare_data(data)

        # Extract list of all station visits
        station_series = sorted(data["SERNO_STN"].unique())

        # Initialize all stations
        self._stations = {
            series: Station(
                series, self._data[self._data["SERNO_STN"] == series], self._geo_info
            )
            for series in station_series
        }
        self._station_navigator.load_stations(self._stations)
        self._map.load_stations(self._stations)
        self.set_station(station or station_series[0])

    def _read_geo_info_file(self):
        if "QCTOOL_GEOPACKAGE" not in os.environ:
            print("Environment variable 'QCTOOL_GEOPACKAGE' is missing.")
            user_geopackage_path = Path.home() / "SVAR2022_HELCOM_OSPAR.gpkg"
            if not user_geopackage_path.exists():
                print(
                    f"The file SVAR2022_HELCOM_OSPAR.gpkg is missing from {Path.home()}\n"
                    f"copy the file from havgem to {Path.home()}"
                )
            else:
                self.geopackage_path = user_geopackage_path
        else:
            self.geopackage_path = Path(os.environ["QCTOOL_GEOPACKAGE"])

        # Läs in specifika lager från filen
        layers = []
        for layer, area_tag in GEOLAYERS_AREATAG.items():
            print(area_tag)
            # Läs in varje lager och döp om vald kolumn till "area_tag"
            t0 = time.perf_counter()
            gdf = gpd.read_file(self.geopackage_path, layer=layer)
            t1 = time.perf_counter()
            print(f"First read file took ({t1-t0:.3f} .s)\nshould be no more read")
            gdf = gdf.rename(columns={area_tag: "area_tag"})
            layers.append(gdf)

        # Kombinera lagren till en enda GeoDataFrame
        self._geo_info = pd.concat(layers, ignore_index=True)


QcTool()
