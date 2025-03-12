import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from bokeh.models import Column, Row, TabPanel, Tabs
from bokeh.plotting import curdoc
from nodc_statistics import regions
from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskemqc import FysKemQc

from qc_tool.data_transformation import changes_report, prepare_data
from qc_tool.file_handler import FileHandler
from qc_tool.flag_info import FlagInfo
from qc_tool.manual_qc_handler import ManualQcHandler
from qc_tool.map import Map
from qc_tool.metadata_qc_handler import MetadataQcHandler
from qc_tool.profile_slot import ProfileSlot
from qc_tool.scatter_slot import ScatterSlot
from qc_tool.static.station_navigator import StationNavigator
from qc_tool.station import Station
from qc_tool.station_info import StationInfo

GEOLAYERS_AREATAG = {
    "SVAR2022_typomrkust_lagad": "TYPOMRKUST",
    "ospar_subregions_20160418_3857_lagad": "area_tag",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3_lagad": "level_34",
}


class QcTool:
    def __init__(self):
        self._data = None
        self._stations = {}
        self._selected_station = None

        self._station_navigator = StationNavigator(self.set_station)
        self._station_info = StationInfo()
        self._map = Map(self.set_station)
        self._read_geo_info_file()

        self._file_handler = FileHandler(
            self.load_file_callback,
            self.save_file_callback,
            self.save_diff_file_callback,
            self.automatic_qc_callback,
        )
        self._flag_info = FlagInfo()
        self._manual_qc_handler = ManualQcHandler(self.manual_qc_callback)
        self._metadata_qc_handler = MetadataQcHandler()

        # Parameters
        first_chemical_parameter = ProfileSlot(
            parameter="DOXY_BTL",
            value_selected_callback=self.select_values_callback,
        )
        first_chemical_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._chemical_profile_parameters = [
            first_chemical_parameter,
            ProfileSlot(
                linked_parameter=first_chemical_parameter,
                parameter="PHOS",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_chemical_parameter,
                parameter="NTRI",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_chemical_parameter,
                parameter="NTRA",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_chemical_parameter,
                parameter="AMON",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_chemical_parameter,
                parameter="SIO3-SI",
                value_selected_callback=self.select_values_callback,
            ),
        ]

        first_physical_parameter = ProfileSlot(
            parameter="SALT_CTD",
            value_selected_callback=self.select_values_callback,
        )
        first_physical_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._physical_profile_parameters = [
            first_physical_parameter,
            ProfileSlot(
                linked_parameter=first_physical_parameter,
                parameter="TEMP_CTD",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_physical_parameter,
                parameter="DOXY_CTD",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_physical_parameter,
                parameter="DOXY_BTL",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_physical_parameter,
                parameter="H2S",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_physical_parameter,
                parameter="CHLFL",
                value_selected_callback=self.select_values_callback,
            ),
        ]

        first_biological_parameter = ProfileSlot(
            parameter="CPHL",
            value_selected_callback=self.select_values_callback,
        )
        first_biological_parameter._figure.yaxis.axis_label = "Depth [m]"
        self._biological_profile_parameters = [
            first_biological_parameter,
            ProfileSlot(
                linked_parameter=first_biological_parameter,
                parameter="PH_LAB",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_biological_parameter,
                parameter="ALKY",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_biological_parameter,
                parameter="HUMUS",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_biological_parameter,
                parameter="CHLFL",
                value_selected_callback=self.select_values_callback,
            ),
            ProfileSlot(
                linked_parameter=first_biological_parameter,
                parameter="SALT_CTD",
                value_selected_callback=self.select_values_callback,
            ),
        ]

        self._scatter_parameters = [
            ScatterSlot(x_parameter="DOXY_BTL", y_parameter="DOXY_CTD"),
            ScatterSlot(x_parameter="ALKY", y_parameter="SALT_CTD"),
            ScatterSlot(x_parameter="PHOS", y_parameter="NTRZ"),
            ScatterSlot(x_parameter="NTRZ", y_parameter="H2S"),
        ]

        # Top row
        station_info_column = Column(
            self._station_navigator.layout, self._station_info.layout
        )
        files_tab = TabPanel(title="Files", child=self._file_handler.layout)
        meta_data_cq_tab = TabPanel(
            title="Metadata QC", child=self._metadata_qc_handler.layout
        )
        manual_qc_tab = TabPanel(title="Manual QC", child=self._manual_qc_handler.layout)

        self._extra_info_tabs = Tabs(tabs=[files_tab, meta_data_cq_tab, manual_qc_tab])
        self.flags_info = Column(self._flag_info.layout)

        top_row = Row(
            self._map.layout, station_info_column, self._extra_info_tabs, self.flags_info
        )

        # Tab for profile plots
        chemical_profile_row = Row(
            children=[parameter.layout for parameter in self._chemical_profile_parameters]
        )

        physical_profile_row = Row(
            children=[parameter.layout for parameter in self._physical_profile_parameters]
        )

        biological_profile_row = Row(
            children=[
                parameter.layout for parameter in self._biological_profile_parameters
            ]
        )

        profile_tab = TabPanel(
            child=Column(
                chemical_profile_row, physical_profile_row, biological_profile_row
            ),
            title="Profiles",
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
        """Called when a cruise has been loaded from disk."""
        data = self._match_sea_basins(data)
        data = prepare_data(data)
        self._set_data(data)

    def save_file_callback(self, filename: Path):
        self._data.to_csv(filename, sep="\t")

    def save_diff_file_callback(self, filename: Path):
        changes_report(self._data).to_csv(filename, sep="\t")

    def automatic_qc_callback(self):
        """Called when automatic qc has been requested."""
        print("Automatic QC started...")
        t0 = time.perf_counter()
        fys_kem_qc = FysKemQc(self._data)
        fys_kem_qc.run_automatic_qc()
        t1 = time.perf_counter()
        print(f"Automatic QC finished ({t1-t0:.3f} s.)")
        self._data[["INCOMING_QC", "AUTO_QC", "MANUAL_QC", "TOTAL_QC"]] = self._data[
            "quality_flag_long"
        ].str.split("_", expand=True)
        self._set_data(self._data, self._selected_station.visit_key)

    def metadata_qc_callback(self):
        print("Metadata QC started...")
        t0 = time.perf_counter()
        for station in self._stations.values():
            station.run_metadata_qc()
        t1 = time.perf_counter()
        print(f"Metadata QC finished ({t1-t0:.3f} s.)")
        self._station_info.update()
        self._metadata_qc_handler.update()

    def manual_qc_callback(self, values: list[Parameter]):
        """ "Called when manual qc has been applied."""
        # Update quality flag in data
        t0 = time.perf_counter()
        for value in values:
            self._data.loc[
                (self._data["SERNO"] == value._data["SERNO"])
                & (self._data["parameter"] == value._data["parameter"])
                & (self._data["DEPH"] == value._data["DEPH"]),
                "quality_flag_long",
            ] = str(value.qc)
        t1 = time.perf_counter()
        print(f"Manual QC finished ({t1-t0:.3f} s.)")

        self._data[["INCOMING_QC", "AUTO_QC", "MANUAL_QC", "TOTAL_QC"]] = self._data[
            "quality_flag_long"
        ].str.split("_", expand=True)
        # Reload data
        self._set_data(self._data, self._selected_station.visit_key)

    def set_station(self, station_visit: str):
        self._station_navigator.set_station(station_visit)
        self._selected_station = self._stations[station_visit]
        self._station_info.set_station(self._selected_station)
        self._map.set_station(self._selected_station.visit_key)
        self._manual_qc_handler.select_values()
        self._metadata_qc_handler.set_station(self._selected_station)
        if self._selected_station._visit.qc_log:
            self._set_extra_info_tab(1)

        for parameter in self._chemical_profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._physical_profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._biological_profile_parameters:
            parameter.update_station(self._selected_station)

        for parameter in self._scatter_parameters:
            parameter.update_station(self._selected_station)

    def select_values_callback(self, values, sender):
        for profile_slot in (
            self._chemical_profile_parameters
            + self._physical_profile_parameters
            + self._biological_profile_parameters
        ):
            self._set_extra_info_tab(3)

            if profile_slot is sender:
                continue
            profile_slot.clear_selection()
        self._manual_qc_handler.select_values(values)

    def _match_sea_basins(self, data):
        if self._geo_info is None:
            return data

        print("Matching sea basins...")
        t0 = time.perf_counter()
        # Assuming df is your DataFrame and regions.sea_basin_for_position is the function
        # to apply
        # Step 1: Extract unique combinations of LONGI and LATIT
        unique_positions = data[["LONGI", "LATIT"]].drop_duplicates()
        # Step 2: Apply the function to each unique combination
        unique_positions["sea_basin"] = unique_positions.apply(
            lambda row: regions.sea_basin_for_position(
                dms_to_dd(row["LONGI"]), dms_to_dd(row["LATIT"]), self._geo_info
            ),
            axis=1,
        )
        # Step 3: Map the results back to the original DataFrame
        data = data.merge(unique_positions, on=["LONGI", "LATIT"], how="left")
        t1 = time.perf_counter()
        print(f"Matching sea basins finished ({t1-t0:.3f} s.)")
        return data

    def _set_data(self, data: pd.DataFrame, station: str = None):
        self._data = data

        # Extract list of all station visits
        station_visit = sorted(data["visit_key"].unique())

        # Initialize all stations
        self._stations = {
            visit_key: Station(
                visit_key,
                self._data[self._data["visit_key"] == visit_key],
                self._geo_info,
            )
            for visit_key in station_visit
        }
        self._station_navigator.load_stations(self._stations)
        self._map.load_stations(self._stations)
        self.metadata_qc_callback()
        self.set_station(station or station_visit[0])

    def _read_geo_info_file(self):
        """Read geographic definitions of all sea basins."""
        geopackage_path = Path.home() / "SVAR2022_HELCOM_OSPAR_vs2.gpkg"

        if not geopackage_path.exists():
            print(
                f"In order to retrieve statistics for the station, the file "
                f"'SVAR2022_HELCOM_OSPAR_vs2.gpkg' is needed.\n"
                f"Either place the file in your home directory ({Path.home()}) or "
                f"specify a location with the environment variable 'QCTOOL_GEOPACKAGE'."
            )
            self._geo_info = None
            return

        # Read specific layers from the file
        t0 = time.perf_counter()
        print(f"Extracting basins from geopackage file {geopackage_path}...")

        layers = []
        for layer, area_tag in GEOLAYERS_AREATAG.items():
            # Read the layer and rename column to 'area_tag'
            gdf = gpd.read_file(geopackage_path, layer=layer)
            gdf = gdf.rename(columns={area_tag: "area_tag"})
            layers.append(gdf)

        # Combine the layers to a single GeoDataFrame
        self._geo_info = pd.concat(layers, ignore_index=True)

        t1 = time.perf_counter()
        print(f"Extracting basins from geopackage file finished ({t1 - t0:.3f} s.)")

    def _set_extra_info_tab(self, index: int):
        self._extra_info_tabs.active = index


def dms_to_dd(dms):
    """Convert a position between DMS and DD"""
    degrees, remainder = divmod(dms, 100)
    return degrees + remainder / 60


QcTool()
