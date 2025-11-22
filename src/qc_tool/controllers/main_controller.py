import time
from pathlib import Path

import geopandas
import pandas as pd
from pyproj import Transformer

from qc_tool.app_state import AppState
from qc_tool.controllers.filter_controller import FilterController
from qc_tool.controllers.summary_controller import SummaryController
from qc_tool.controllers.visits_browser_controller import VisitsBrowserController
from qc_tool.controllers.visits_controller import VisitsController
from qc_tool.data_transformation import changes_report

GEOLAYERS_AREATAG = {
    "SVAR2022_typomrkust_lagad": "TYPOMRKUST",
    "ospar_subregions_20160418_3857_lagad": "area_tag",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3_lagad": "level_34",
}


class MainController:
    def __init__(self, app_state: AppState):
        self._state = app_state
        self._main_view = None

        self._visits_controller = VisitsController(
            visits_model=self._state.visits, file_model=self._state.file
        )

        self._transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")

        self.filter_controller = FilterController(self._state.visits, self._state.filter)

        self.summary_controller = SummaryController(
            file_model=self._state.file,
            visits_model=self._state.visits,
            map_model=self._state.map,
            validation_log_model=self._state.validation_log,
        )
        self.visits_browser_controller = VisitsBrowserController(self._state)


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

    def _set_validation(self, validation: dict):
        self._validation = validation
        self.summary_view.update_validation_log(validation)

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
            gdf = geopandas.rename(columns={area_tag: "area_tag"})
            layers.append(gdf)

        # Combine the layers to a single GeoDataFrame
        self._geo_info = pd.concat(layers, ignore_index=True)

        t1 = time.perf_counter()
        print(f"Extracting basins from geopackage file finished ({t1 - t0:.3f} s.)")

    def _convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes
