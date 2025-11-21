import time
from pathlib import Path

import geopandas
import pandas as pd
import polars as pl

from qc_tool.models.file_model import FileModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.visit import Visit

GEOLAYERS_AREATAG = {
    "SVAR2022_typomrkust_lagad": "TYPOMRKUST",
    "ospar_subregions_20160418_3857_lagad": "area_tag",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3_lagad": "level_34",
}


class VisitsController:
    def __init__(self, file_model: FileModel, visits_model: VisitsModel):
        self._file_model = file_model
        self._geo_info = None
        self._visits_model = visits_model
        self._file_model.register_listener(self._file_model.NEW_DATA, self._on_new_data)
        self._visits_model.register_listener(
            self._visits_model.NEW_VISITS, self._on_new_visits
        )

    def _on_new_data(self):
        # Extract list of all station visits
        station_visit = sorted(self._file_model.data["visit_key"].unique())

        # Initialize all visits
        visits = {
            visit_key: Visit(
                visit_key,
                self._file_model.data.filter(pl.col("visit_key") == visit_key),
                self._geo_info,
            )
            for visit_key in station_visit
        }

        self._visits_model.set_visits(visits)

    def _on_new_visits(self):
        print("visits_controller._visits_updated()")
        self._visits_model.set_visit(self._visits_model.visit_by_index(0))

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
