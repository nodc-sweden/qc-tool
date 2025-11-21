import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.profiles_controller import ProfilesController

import time
from pathlib import Path

import geopandas
import jinja2
import pandas as pd
import polars as pl
from bokeh.io import curdoc
from bokeh.models.layouts import Column, Row, TabPanel, Tabs
from nodc_statistics import regions
from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskemqc import FysKemQc

from qc_tool.app_state import AppState
from qc_tool.data_transformation import changes_report, prepare_data
from qc_tool.file_handler import FileHandler
from qc_tool.manual_qc_handler import ManualQcHandler
from qc_tool.metadata_qc_handler import MetadataQcHandler
from qc_tool.scatter_slot import ScatterSlot
from qc_tool.views.base_view import BaseView
from qc_tool.views.map_view import MapView
from qc_tool.views.parameter_selector_view import ParameterSelectorView
from qc_tool.views.profile_grid_view import ProfileGridView
from qc_tool.views.visit_info_view import VisitInfoView
from qc_tool.views.visit_selector_view import VisitSelectorView
from qc_tool.visit import Visit

GEOLAYERS_AREATAG = {
    "SVAR2022_typomrkust_lagad": "TYPOMRKUST",
    "ospar_subregions_20160418_3857_lagad": "area_tag",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3_lagad": "level_34",
}


_validation_log_template = jinja2.Template("""
{% for key, value in validation.items() %}
  <div class="collapsible-container">
    <input id="collapsible-{{ key }}" class="toggle" type="checkbox">
    <label for="collapsible-{{ key }}" class="toggle-label{% if value.fail_count %} errors{% endif %}">{{ key }} ({{ value.success_count }} successes, {{ value.fail_count }} errors)</label>
    <div class="collapsible-content">
      <div class="content-inner">
      {% if value.fail %}
        <p>{{ value.description }}</p>
        <ul>
        {% for category, fail_rows in value.fail.items() %}
          {% if category != "General" %}
          <li>{{ category }}</li>
            <ul>
          {% endif %}
          {% for fail_row in fail_rows %}
              <li>{{ fail_row }}</li>
          {% endfor %}
          {% if category != "General" %}
            </ul>
          {% endif %}
        {% endfor %}
        </ul>
      {% else %}
        <p>No validation errors.</p>
      {% endif %}
      </div>
    </div>
  </div>
{% endfor %}
""")  # noqa: E501

physical_parameters = (
    "SALT_CTD",
    "SALT_BTL",
    "TEMP_CTD",
    "TEMP_BTL",
    "DOXY_CTD",
    "DOXY_BTL",
    "H2S",
    "CHLFL",
)

chemical_parameters = (
    "SIO3-SI",
    "PHOS",
    "PTOT",
    "NTOT",
    "AMON",
    "NTRI",
    "NTRA",
    "NTRZ",
)

biological_parameters = ("CPHL", "CHLFL", "PH_LAB", "PH_TOT", "ALKY", "HUMUS")


class ProfilesView(BaseView):
    def __init__(
        self,
        controller: "ProfilesController",
        state: AppState,
        map_controller,
        visit_selector_controller,
        profile_grid_controller,
    ):
        self._controller = controller
        self._controller.profile_view = self

        self._state = state

        self._map_view = MapView(map_controller, state.map, 400, 300)
        self._station_navigator = VisitSelectorView(
            visit_selector_controller, state.visits
        )

        self._station_info = VisitInfoView(
            controller.visit_info_controller, state.visits, width=400
        )

        self._file_handler = FileHandler(
            self.load_file_callback,
            self.save_file_callback,
            self.save_diff_file_callback,
            self.automatic_qc_callback,
        )

        self._read_geo_info_file()
        self._manual_qc_handler = ManualQcHandler(self.manual_qc_callback)
        self._metadata_qc_handler = MetadataQcHandler()

        self._scatter_parameters = [
            ScatterSlot(x_parameter="DOXY_BTL", y_parameter="DOXY_CTD"),
            ScatterSlot(x_parameter="ALKY", y_parameter="SALT_CTD"),
            ScatterSlot(x_parameter="PHOS", y_parameter="NTRZ"),
            ScatterSlot(x_parameter="NTRZ", y_parameter="H2S"),
        ]

        # Top row
        navigation_column = Column(
            self._station_navigator.layout,
            self._map_view.layout,
            sizing_mode="stretch_both",
            width=400,
        )

        self._parameter_handler = ParameterSelectorView(
            self._controller.parameter_selector_controller,
            self._state.parameters,
            self._state.profile_grid,
        )

        meta_data_cq_tab = TabPanel(
            title="Metadata QC", child=self._metadata_qc_handler.layout
        )
        manual_qc_tab = TabPanel(title="Manual QC", child=self._manual_qc_handler.layout)

        self._extra_info_tabs = Tabs(
            tabs=[meta_data_cq_tab, manual_qc_tab], sizing_mode="stretch_both"
        )

        top_row = Row(
            navigation_column,
            self._station_info.layout,
            self._parameter_handler.layout,
            self._extra_info_tabs,
            sizing_mode="stretch_width",
        )

        self._profile_tab_handler = ProfileGridView(
            profile_grid_controller, state.profile_grid, state.parameters, state.visits
        )

        self._profile_tab = TabPanel(
            child=self._profile_tab_handler.layout,
            title="Profiles",
        )

        # Tab for scatter plots
        scatter_tab = TabPanel(
            child=Row(
                children=[parameter.layout for parameter in self._scatter_parameters]
            ),
            title="Scatter",
        )

        bottom_row = Tabs(tabs=[self._profile_tab, scatter_tab])

        # Full layout
        self._layout = Column(top_row, bottom_row)

    def load_file_callback(self, data: pl.DataFrame, validation: dict):
        data = self._match_sea_basins(data)
        data = prepare_data(data)
        self._set_data(data)
        self._set_validation(validation)

    def save_file_callback(self, filename: Path):
        self._data.write_csv(filename, separator="\t")

    def save_diff_file_callback(self, filename: Path):
        changes_report(self._data).write_excel(
            filename,
            header_format={"bold": True, "border": 2},
            freeze_panes=(1, 0),
            column_formats={
                "LATIT": "0.00",
                "LONGI": "0.00",
                "value": "0.00",
                "DEPH": "0.00",
                "WADEP": "0.00",
            },
        )

    def automatic_qc_callback(self):
        """Called when automatic qc has been requested."""
        print("Automatic QC started...")
        t0 = time.perf_counter()
        fys_kem_qc = FysKemQc(self._data)
        fys_kem_qc.run_automatic_qc()
        fys_kem_qc.total_flag_info()
        self._data = fys_kem_qc._data
        t1 = time.perf_counter()
        print(f"Automatic QC finished ({t1 - t0:.3f} s.)")

        self._set_data(self._data, self._selected_station.visit_key)

    def parameter_handler_callback(self, *, columns, rows):
        self._profile_tab_handler.sync_profiles(columns=columns, rows=rows)
        self._profile_tab.child = self._profile_tab_handler.layout

    def manual_qc_callback(self, values: list[Parameter]):
        """Called when manual qc has been applied."""
        # Update quality flag in data
        t0 = time.perf_counter()
        for value in values:
            self._data = self._data.with_columns(
                pl.when(
                    (pl.col("SERNO") == value._data["SERNO"])
                    & (pl.col("parameter") == value._data["parameter"])
                    & (pl.col("DEPH") == value._data["DEPH"])
                )
                .then(pl.lit(str(value.qc)))
                .otherwise(pl.col("quality_flag_long"))
                .alias("quality_flag_long")
            )
        t1 = time.perf_counter()
        print(f"Manual QC finished ({t1 - t0:.3f} s.)")

        # Reload data
        self._set_data(self._data, self._selected_station.visit_key)

    def set_station(self, station_visit: str):
        self._station_navigator.set_visit(station_visit)
        self._selected_station = self._stations[station_visit]
        # self._station_info.set_station(self._selected_station)
        self._map_view.set_station(self._selected_station.visit_key)
        self._manual_qc_handler.select_values()
        self._metadata_qc_handler.set_station(self._selected_station)
        if self._selected_station._metadata_visit.qc_log:
            self._set_extra_info_tab(1)

        document = curdoc()
        document.hold("combine")
        # self._profile_tab_handler.set_station(self._selected_station)
        document.unhold()

    def _match_sea_basins(self, data):
        if self._geo_info is None:
            return data

        print("Matching sea basins...")
        t0 = time.perf_counter()
        # Step 1: Extract unique positions and create decimal degree columns
        positions_dd_pl = data.select(
            ["sample_longitude_dd", "sample_latitude_dd"]
        ).unique()

        # Step 2: Call the bulk function
        positions_dd = [
            (lon, lat)
            for lon, lat in positions_dd_pl.select(
                ["sample_longitude_dd", "sample_latitude_dd"]
            ).to_numpy()
        ]
        basins_dict = regions.sea_basins_for_positions(
            positions_dd, geo_info=self._geo_info
        )
        basins_pl = pl.DataFrame(basins_dict).rename(
            {"LONGI_DD": "sample_longitude_dd", "LATIT_DD": "sample_latitude_dd"}
        )

        # Step 3: Join the sea_basins back to the unique positions, drop DD columns
        positions_with_basins = positions_dd_pl.join(
            basins_pl, on=["sample_longitude_dd", "sample_latitude_dd"], how="left"
        )

        # Step 4: Join back to the original data
        data = data.join(
            positions_with_basins,
            on=["sample_longitude_dd", "sample_latitude_dd"],
            how="left",
        )

        t1 = time.perf_counter()
        print(f"Matching sea basins finished ({t1 - t0:.3f} s.)")

        return data

    def _set_data(self, data: pl.DataFrame, station: str | None = None):
        """Ensure QC columns always reflect quality_flag_long."""
        if not data.is_empty():
            split = (
                pl.col("quality_flag_long")
                .str.split_exact("_", 3)
                .struct.rename_fields(["INCOMING_QC", "AUTO_QC", "MANUAL_QC", "TOTAL_QC"])
                .alias("split_qc_fields")
            )

            # Drop existing QC columns to avoid duplicates
            qc_cols = ["INCOMING_QC", "AUTO_QC", "MANUAL_QC", "TOTAL_QC"]
            data = data.drop([c for c in qc_cols if c in data.columns])

            self._data = data.with_columns(split).unnest("split_qc_fields")
        else:
            self._data = data

        # Extract list of all station visits
        station_visit = sorted(data["visit_key"].unique())

        # Initialize all stations
        self._stations = {
            visit_key: Visit(
                visit_key,
                self._data.filter(pl.col("visit_key") == visit_key),
                self._geo_info,
            )
            for visit_key in station_visit
        }
        self._station_navigator.load_stations(self._stations)
        self._map_view.load_stations(self._stations)
        # self._parameter_handler.reset_selection()
        self.set_station(station or station_visit[0])

    def _set_extra_info_tab(self, index: int):
        self._extra_info_tabs.active = index

    def _set_validation(self, validation: dict):
        self._validation = validation
        self._log_div.text = _validation_log_template.render(validation=validation)

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
            gdf = geopandas.read_file(geopackage_path, layer=layer)
            gdf = gdf.rename(columns={area_tag: "area_tag"})
            layers.append(gdf)

        # Combine the layers to a single GeoDataFrame
        self._geo_info = pd.concat(layers, ignore_index=True)

        t1 = time.perf_counter()
        print(f"Extracting basins from geopackage file finished ({t1 - t0:.3f} s.)")

    @property
    def layout(self):
        return self._layout
