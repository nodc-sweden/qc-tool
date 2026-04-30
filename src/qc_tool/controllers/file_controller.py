import os
import time
from pathlib import Path

import geopandas
import nodc_station
import pandas as pd
import polars as pl
from nodc_statistics import regions
from ocean_data_qc.fyskem.qc_flag import QcFlag
from ocean_data_qc.fyskemqc import FysKemQc, QcFlags
from sharkadm import (
    adm_logger,
    exporters,
    multi_transformers,
    transformers,
    validators,
)
from sharkadm import (
    controller as sharkadm_controller,
)

from qc_tool.data_transformation import changes_report, prepare_data
from qc_tool.models.file_model import FileModel
from qc_tool.models.geo_info_model import GeoInfoModel
from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.models.validation_log_model import ValidationLogModel
from qc_tool.views.file_view import FileView

CONFIG_ENV = "NODC_CONFIG"

_home = Path.home()
OTHER_CONFIG_SOURCES = [
    _home / "NODC_CONFIG",
    _home / ".NODC_CONFIG",
    _home / "nodc_config",
    _home / ".nodc_config",
]

GEOLAYERS_AREATAG = {
    "SVAR2022_typomrkust_lagad": "TYPOMRKUST",
    "ospar_subregions_20160418_3857_lagad": "area_tag",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3_lagad": "level_34",
}


class FileController:
    def __init__(
        self,
        file_model: FileModel,
        validation_log_model: ValidationLogModel,
        manual_qc_model: ManualQcModel,
        geo_info_model: GeoInfoModel,
    ):
        self._file_model = file_model
        self._file_model.register_listener(FileModel.NEW_DATA, self._on_new_data)
        self._file_model.register_listener(FileModel.LOAD_ABORTED, self._on_load_aborted)
        self._file_model.register_listener(FileModel.UPDATED_DATA, self._on_feedback_load)

        self._validation_log_model = validation_log_model

        self._manual_qc_model = manual_qc_model
        self._manual_qc_model.register_listener(
            ManualQcModel.QC_PERFORMED, self._on_qc_performed
        )

        self._geo_info_model = geo_info_model

        self.file_view: FileView = None
        shapefile_t0 = time.perf_counter()
        self._ocean_shapefile = _load_ocean_shapefile()
        shapefile_t1 = time.perf_counter()
        print(f"\tOpening ocean shapefile: {shapefile_t1 - shapefile_t0:.3f} s.")

    @property
    def file_model(self):
        return self._file_model

    @property
    def ocean_shapefile(self):
        return self._ocean_shapefile

    def load_file(self, file_path, add_to_existing: bool = False):
        if add_to_existing and file_path in self._file_model.file_paths:
            self.file_model.no_new_data()
            return

        print(f"Loading data from {file_path}...")
        try:
            controller = sharkadm_controller.get_polars_controller_with_data(file_path)
        except Exception:  # noqa: BLE001
            # Catching exceptions this broadly is not recommended, but sharkadm does not
            # guarantee a specific exception.
            self._file_model.no_new_data()
            return

        self._reset_validation_logs()
        self._apply_transformers(controller)
        self._run_validators(controller)
        self._apply_post_transformers(controller)
        print("Data loaded")
        data = controller.export(
            exporters.PolarsDataFrame(header_as="PhysicalChemical", float_columns=False)
        )
        data = self._match_sea_basins(data)
        data = prepare_data(data)
        data = self._run_automatic_qc(data)
        data = self._expand_quality_flag_long(data)
        if add_to_existing and self._file_model.data is not None:
            existing_keys = set(self._file_model.data["visit_key"].unique())
            new_keys = set(data["visit_key"].unique())
            overlap = existing_keys & new_keys
            if overlap:
                print(f"WARNING: {len(overlap)} visit_key(s) already loaded: {overlap}")
        self._file_model.add_data(data, file_path, add_to_existing)
        adm_logger.filter(log_types=[adm_logger.VALIDATION], level=">warning")
        self._validation_log_model.set_validation_log(adm_logger.data, add_to_existing)

    def load_working_file(self, path, raw_data: pl.DataFrame):
        selected_path = Path(path)
        working_data = pl.read_csv(
            selected_path,
            schema_overrides={"DEPH": pl.Float64},
            separator="\t",
            has_header=True,
            infer_schema_length=0,
            encoding="utf8",
        )
        joined_data = self.apply_working_file(
            raw_data=raw_data, working_data=working_data
        )
        self._file_model.data_flags_update(joined_data)

    def save_data_for_source(self, source_path: Path, file_path: Path):
        self._file_model.data.filter(pl.col("source") == str(source_path)).write_csv(
            file_path, separator="\t"
        )

    def save_changed_data(self, file_path: Path):
        changes_report(self._file_model.data).write_excel(
            file_path,
            header_format={"bold": True, "border": 2},
            freeze_panes=(1, 0),
        )

    def _on_new_data(self):
        self.file_view.file_load_completed()

    def _on_load_aborted(self):
        self.file_view.file_load_completed()

    def _on_feedback_load(self):
        self.file_view.feedback_load_completed()

    def _on_qc_performed(self):
        t0 = time.perf_counter()
        data = self._file_model.data
        for value in self._manual_qc_model.selected_values:
            data = data.with_columns(
                pl.when(
                    (pl.col("visit_key") == value._data["visit_key"])
                    & (pl.col("parameter") == value._data["parameter"])
                    & (pl.col("DEPH") == value._data["DEPH"])
                )
                .then(pl.lit(str(value.qc)))
                .otherwise(pl.col("quality_flag_long"))
                .alias("quality_flag_long")
            )

        category = self._manual_qc_model.comment_category
        comment = self._manual_qc_model.comment
        if category:
            for value in self._manual_qc_model.selected_values:
                for col_name, col_value in [
                    ("MANUAL_QC_CATEGORY", category),
                    ("MANUAL_QC_COMMENT", comment),
                ]:
                    if col_name not in data.columns:
                        data = data.with_columns(
                            pl.lit(None).cast(pl.Utf8).alias(col_name)
                        )
                    data = data.with_columns(
                        pl.when(
                            (pl.col("visit_key") == value._data["visit_key"])
                            & (pl.col("parameter") == value._data["parameter"])
                            & (pl.col("DEPH") == value._data["DEPH"])
                        )
                        .then(pl.lit(col_value))
                        .otherwise(pl.col(col_name))
                        .alias(col_name)
                    )

        data = self._expand_quality_flag_long(data)
        self._file_model.flags_update(data)
        t1 = time.perf_counter()
        print(f"Manual QC finished ({t1 - t0:.3f} s.)")
        self._file_model.manual_flags_update()

    def _reset_validation_logs(self):
        adm_logger.reset_log()

    def _apply_transformers(self, controller):
        print("Running SHARKadm transformers...")
        t0 = time.perf_counter()
        for transformer, args, kwargs in (
            (transformers.AddCtdKust, (), {}),
            (transformers.PolarsRemoveNonDataLines, (), {}),
            (transformers.PolarsReplaceCommaWithDot, (), {}),
            (multi_transformers.DateTimePolars, (), {}),
            (multi_transformers.PositionPolars, (), {}),
            (transformers.PolarsAddVisitKey, (), {}),
            (transformers.PolarsAddPressure, (), {}),
            (transformers.PolarsAddDensityWide, ("CTD",), {}),
            (transformers.PolarsAddDensityWide, ("BTL",), {}),
            (transformers.PolarsAddOxygenSaturationWide, ("CTD",), {}),
            (transformers.PolarsAddOxygenSaturationWide, ("BTL",), {}),
            (transformers.PolarsWideToLong, (), {}),
            (transformers.PolarsMoveLessThanFlagRowFormat, (), {}),
            (transformers.PolarsMoveLargerThanFlagRowFormat, (), {}),
            (transformers.PolarsConvertFlagsToSDN, (), {}),
            (transformers.PolarsAddAnalyseInfo, (), {}),
            (transformers.PolarsAddLmqnt, (), {}),
            (transformers.PolarsAddUncertainty, (), {}),
            (transformers.PolarsRemoveColumns, ("COPY_VARIABLE.*",), {}),
            (
                transformers.PolarsMapperParameterColumn,
                (),
                {"import_column": "SHARKarchive"},
            ),
        ):
            tn_0 = time.perf_counter()
            controller.transform(transformer(*args, **kwargs))
            tn_1 = time.perf_counter()
            print(f"\t{transformer.__name__}: {tn_1 - tn_0:.3f} s.")

        t1 = time.perf_counter()
        print(f"SHARKadm transformers finished ({t1 - t0:.3f} s.)")

    def _define_validators_and_parameters(self):
        validators_and_parameters = (
            (validators.ValidateCommonValuesByVisit, {}),
            (
                validators.ValidateCoordinatesDm,
                {
                    "latitude_dm_column": "visit_reported_latitude",
                    "longitude_dm_column": "visit_reported_longitude",
                },
            ),
            (validators.ValidateDateAndTime, {}),
            (
                validators.ValidatePositionInOcean,
                {
                    "ocean_shapefile": self.ocean_shapefile,
                    "station_name_key": "reported_station_name",
                    "latitude_key": "sample_sweref99tm_y",
                    "longitude_key": "sample_sweref99tm_x",
                },
            ),
            (validators.ValidateWaterDepth, {}),
            (validators.ValidateSampleDepth, {}),
            (validators.ValidateSecchiDepth, {}),
            (validators.ValidateSerialNumber, {}),
            (validators.ValidateSpeed, {}),
            (
                validators.ValidateStationIdentity,
                {
                    "stations": nodc_station.get_station_object(case_sensitive=False),
                    "latitude_key": "sample_sweref99tm_y",
                    "longitude_key": "sample_sweref99tm_x",
                },
            ),
            (validators.ValidateWindir, {}),
            (validators.ValidateWinsp, {}),
            (validators.ValidateAirtemp, {}),
            (validators.ValidateAirpres, {}),
            (validators.ValidateWeath, {}),
            (validators.ValidateCloud, {}),
            (validators.ValidateWeatherConsistency, {}),
            (validators.ValidateWaves, {}),
            (validators.ValidateIceob, {}),
        )

        return validators_and_parameters

    def _run_validators(self, controller):
        print("Running SHARKadm validators...")
        t0 = time.perf_counter()
        for validator, parameters in self._define_validators_and_parameters():
            tn_0 = time.perf_counter()
            controller.validate(validator(**parameters))
            tn_1 = time.perf_counter()
            print(f"\t{validator(**parameters).name}: {tn_1 - tn_0:.3f} s.")

        t1 = time.perf_counter()
        print(f"SHARKadm validators finished ({t1 - t0:.3f} s.)")

    def _apply_post_transformers(self, controller):
        print("Running SHARKadm post transformers...")
        reported_cols = (
            "visit_year",
            "water_depth_m",
            "wind_speed_ms",
            "air_temperature_degc",
            "air_pressure_hpa",
            "sample_depth_m",
        )
        float_cols = [
            "sample_latitude_dd",
            "sample_longitude_dd",
            "water_depth_m",
            "wind_speed_ms",
            "air_temperature_degc",
            "air_pressure_hpa",
            "sample_depth_m",
            "value",
        ]
        int_cols = [
            "visit_year",
            "visit_month",
        ]
        t0 = time.perf_counter()
        for transformer, args, kwargs in (
            (transformers.AddColumnsWithPrefix, (reported_cols, "reported"), {}),
            (transformers.PolarsAddFloatColumns, (float_cols, float_cols), {}),
            (transformers.PolarsAddIntColumns, (int_cols, int_cols), {}),
        ):
            tn_0 = time.perf_counter()
            controller.transform(transformer(*args, **kwargs))
            tn_1 = time.perf_counter()
            print(f"\t{transformer.__name__}: {tn_1 - tn_0:.3f} s.")

        t1 = time.perf_counter()
        print(f"SHARKadm post transformers finished ({t1 - t0:.3f} s.)")

    def _match_sea_basins(self, data):
        if self._geo_info_model.geo_info is None:
            self._read_geo_info()

        print("Matching sea basins...")
        t0 = time.perf_counter()
        # Step 1: Extract unique positions and create decimal degree columns
        unique_positions = data.select(
            ["sample_longitude_dd", "sample_latitude_dd"]
        ).unique()

        # Step 2: Call the bulk function
        positions_dd = [
            (lon, lat)
            for lon, lat in unique_positions.select(
                ["sample_longitude_dd", "sample_latitude_dd"]
            ).to_numpy()
        ]
        basins_dict = regions.sea_basins_for_positions(
            positions_dd, geo_info=self._geo_info_model.geo_info
        )
        basins = pl.DataFrame(basins_dict).rename(
            {"LONGI_DD": "sample_longitude_dd", "LATIT_DD": "sample_latitude_dd"}
        )

        # Step 3: Join the sea_basins back to the unique positions, drop DD columns
        positions_with_basins = unique_positions.join(
            basins, on=["sample_longitude_dd", "sample_latitude_dd"], how="left"
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

    @staticmethod
    def _expand_quality_flag_long(data):
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

            data = data.with_columns(split).unnest("split_qc_fields")
        return data

    @staticmethod
    def _run_automatic_qc(data):
        print("Automatic QC started...")
        t0 = time.perf_counter()
        fys_kem_qc = FysKemQc(data)
        fys_kem_qc.run_automatic_qc()
        fys_kem_qc.total_flag_info()
        t1 = time.perf_counter()
        print(f"Automatic QC finished ({t1 - t0:.3f} s.)")
        return fys_kem_qc._data

    def _read_geo_info(self):
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
        self._geo_info_model.geo_info = pd.concat(layers, ignore_index=True)

        t1 = time.perf_counter()
        print(f"Extracting basins from geopackage file finished ({t1 - t0:.3f} s.)")

    @staticmethod
    def _apply_manual_flag(qflag_str: str, manual_flag: str) -> str:
        if manual_flag is None:  # <-- skip nulls
            return qflag_str  # just return the original string
        q = QcFlags.from_string(qflag_str)
        try:
            q.manual = QcFlag.parse(manual_flag)
        except ValueError:
            return qflag_str
        return str(q)

    def apply_working_file(self, raw_data: pl.DataFrame, working_data: pl.DataFrame):
        print("applying manual flags from working file....")
        join_columns = ["visit_key", "DEPH", "parameter"]
        value_columns = ["MANUAL_QC", "MANUAL_QC_CATEGORY", "MANUAL_QC_COMMENT"]

        for col in ["MANUAL_QC_CATEGORY", "MANUAL_QC_COMMENT"]:
            if col not in raw_data.columns:
                raw_data = raw_data.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

        working_data = working_data.select(
            [c for c in [*join_columns, *value_columns] if c in working_data.columns]
        ).unique(subset=join_columns, keep="last")

        joined_data = raw_data.join(
            working_data, on=join_columns, how="left", suffix="_working_file"
        )

        has_manual_qc_change = (
            pl.col("MANUAL_QC") != pl.col("MANUAL_QC_working_file")
        ) & pl.col("MANUAL_QC_working_file").is_not_null()

        joined_data = joined_data.with_columns(
            pl.when(has_manual_qc_change)
            .then(
                pl.struct(["quality_flag_long", "MANUAL_QC_working_file"]).map_elements(
                    lambda row: self._apply_manual_flag(
                        row["quality_flag_long"], row["MANUAL_QC_working_file"]
                    ),
                    return_dtype=pl.Utf8,
                )
            )
            .otherwise(pl.col("quality_flag_long"))
            .alias("quality_flag_long"),
            pl.when(has_manual_qc_change)
            .then(pl.col("MANUAL_QC_working_file"))
            .otherwise(pl.col("MANUAL_QC"))
            .alias("MANUAL_QC"),
        )
        joined_data = joined_data.drop("MANUAL_QC_working_file")

        for col in ["MANUAL_QC_CATEGORY", "MANUAL_QC_COMMENT"]:
            feedback_col = f"{col}_working_file"
            if feedback_col in joined_data.columns:
                joined_data = joined_data.with_columns(
                    pl.when(pl.col(feedback_col).is_not_null())
                    .then(pl.col(feedback_col))
                    .otherwise(pl.col(col))
                    .alias(col)
                ).drop(feedback_col)

        joined_data = self._expand_quality_flag_long(joined_data)
        print("data updated with manual flags from working file")
        return joined_data


def _load_ocean_shapefile():
    if _config_dir := _get_config_dir():
        shapefile = (
            _config_dir / "sharkweb_shapefiles" / "Havsomr_SVAR_2016_3c_CP1252.shp"
        )
        if shapefile.exists():
            return geopandas.read_file(shapefile)
    return geopandas.GeoDataFrame()


def _get_config_dir() -> Path | None:
    if config_dir := os.getenv(CONFIG_ENV):
        return Path(config_dir)
    for config_dir in OTHER_CONFIG_SOURCES:
        if config_dir.exists():
            return config_dir
    return None


def _apply_transformers(controller):
    print("Running SHARKadm transformers...")
    t0 = time.perf_counter()
    for transformer, args, kwargs in (
        (transformers.AddCtdKust, (), {}),
        (transformers.PolarsRemoveNonDataLines, (), {}),
        (transformers.PolarsReplaceCommaWithDot, (), {}),
        (multi_transformers.DateTimePolars, (), {}),
        (multi_transformers.PositionPolars, (), {}),
        (transformers.PolarsAddVisitKey, (), {}),
        (transformers.PolarsAddPressure, (), {}),
        (transformers.PolarsAddDensityWide, ("CTD",), {}),
        (transformers.PolarsAddDensityWide, ("BTL",), {}),
        (transformers.PolarsAddOxygenSaturationWide, ("CTD",), {}),
        (transformers.PolarsAddOxygenSaturationWide, ("BTL",), {}),
        (transformers.PolarsWideToLong, (), {}),
        (transformers.PolarsMoveLessThanFlagRowFormat, (), {}),
        (transformers.PolarsMoveLargerThanFlagRowFormat, (), {}),
        (transformers.PolarsConvertFlagsToSDN, (), {}),
        (transformers.PolarsAddAnalyseInfo, (), {}),
        (transformers.PolarsAddLmqnt, (), {}),
        (transformers.PolarsAddUncertainty, (), {}),
        (transformers.PolarsRemoveColumns, ("COPY_VARIABLE.*",), {"regex": True}),
        (
            transformers.PolarsMapperParameterColumn,
            (),
            {"import_column": "SHARKarchive"},
        ),
    ):
        tn_0 = time.perf_counter()
        controller.transform(transformer(*args, **kwargs))
        tn_1 = time.perf_counter()
        print(f"\t{transformer.__name__}: {tn_1 - tn_0:.3f} s.")

    t1 = time.perf_counter()
    print(f"SHARKadm transformers finished ({t1 - t0:.3f} s.)")


if __name__ == "__main__":
    file_path = r"C:/LenaV/code/w_qc-tool/LIMS testdata/jan_2024_klippt_metadatafel/2025-06-24 1630-2024-LANDSKOD 77-FARTYGSKOD 10/Raw_data/data.txt"  # noqa: E501
    controller = sharkadm_controller.get_polars_controller_with_data(file_path)
    _apply_transformers(controller=controller)
    print(controller.data.columns)
    data = controller.export(
        exporters.PolarsDataFrame(header_as="PhysicalChemical", float_columns=False)
    )
    print(data.columns)
