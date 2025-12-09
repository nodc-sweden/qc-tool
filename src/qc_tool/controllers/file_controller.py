import os
import time
from collections import defaultdict
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

        self._mannual_qc_model = manual_qc_model
        self._mannual_qc_model.register_listener(
            ManualQcModel.QC_PERFORMED, self._on_qc_performed
        )

        self._geo_info_model = geo_info_model

        self.file_view = None

    @property
    def file_model(self):
        return self._file_model

    def load_file(self, file_path):
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
        validation_log = self._collect_validation_logs()
        print("Data loaded")
        data = controller.export(
            exporters.PolarsDataFrame(header_as="PhysicalChemical", float_columns=True)
        )
        data = self._match_sea_basins(data)
        data = prepare_data(data)
        data = self._run_automatic_qc(data)
        data = self._expand_quality_flag_long(data)
        self._file_model.add_data(data, file_path)
        self._validation_log_model.set_validation_log(validation_log)

    def load_feedbackfile(self, path, raw_data: pl.DataFrame):
        selected_path = Path(path)
        feedback_data = pl.read_excel(selected_path)
        feedback_data = feedback_data.cast({"DEPH": pl.Float64})
        joined_data = self.apply_feedback_file(
            raw_data=raw_data, feedback_data=feedback_data
        )
        self._file_model.data_flags_update(joined_data)

    def save_data(self, file_path: Path):
        self._file_model.data.write_csv(file_path, separator="\t")

    def save_changed_data(self, file_path: Path):
        changes_report(self._file_model.data).write_excel(
            file_path,
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

    def _on_new_data(self):
        self.file_view.file_load_completed()

    def _on_load_aborted(self):
        self.file_view.file_load_completed()

    def _on_feedback_load(self):
        self.file_view.feedback_load_completed()

    def _on_qc_performed(self):
        t0 = time.perf_counter()
        data = self._file_model.data
        for value in self._mannual_qc_model.selected_values:
            data = data.with_columns(
                pl.when(
                    (pl.col("SERNO") == value._data["SERNO"])
                    & (pl.col("parameter") == value._data["parameter"])
                    & (pl.col("DEPH") == value._data["DEPH"])
                )
                .then(pl.lit(str(value.qc)))
                .otherwise(pl.col("quality_flag_long"))
                .alias("quality_flag_long")
            )
        data = self._expand_quality_flag_long(data)
        self._file_model.data_flags_update(data)
        t1 = time.perf_counter()
        print(f"Manual QC finished ({t1 - t0:.3f} s.)")

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

    def _run_validators(self, controller):
        print("Running SHARKadm validators...")
        t0 = time.perf_counter()

        shapefile_t0 = time.perf_counter()
        ocean_shapefile = _load_ocean_shapefile()
        shapefile_t1 = time.perf_counter()
        print(f"\tOpening ocean shapefile: {shapefile_t1 - shapefile_t0:.3f} s.")

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
                    "ocean_shapefile": ocean_shapefile,
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
        for validator, parameters in validators_and_parameters:
            tn_0 = time.perf_counter()
            validator(**parameters).validate(controller.data_holder)
            tn_1 = time.perf_counter()
            print(f"\t{validator(**parameters).name}: {tn_1 - tn_0:.3f} s.")

        t1 = time.perf_counter()
        print(f"SHARKadm validators finished ({t1 - t0:.3f} s.)")

    def _apply_post_transformers(self, controller):
        print("Running SHARKadm post transformers...")
        reported_cols = (
            "water_depth_m",
            "air_temperature_degc",
            "sample_depth_m",
        )
        float_cols = ["water_depth_m", "air_temperature_degc", "sample_depth_m", "value"]
        t0 = time.perf_counter()
        for transformer, args, kwargs in (
            (transformers.AddColumnsWithPrefix, (reported_cols, "reported"), {}),
            (transformers.PolarsAddFloatColumns, (float_cols, float_cols), {}),
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
            positions_dd, geo_info=self._geo_info_model.geo_info
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

    def _collect_validation_logs(self):
        validation_remarks = defaultdict(
            lambda: {
                "fail": defaultdict(list),
                "success": defaultdict(list),
            }
        )

        adm_logger.filter(log_types=[adm_logger.VALIDATION])

        description_for_validator = {
            validator.get_display_name(): validator.get_validator_description()
            for validator in (
                validators.ValidateCoordinatesDm,
                validators.ValidateDateAndTime,
                validators.ValidateNameInMaster,
                validators.ValidatePositionInOcean,
                validators.ValidatePositionWithinStationRadius,
                validators.ValidatePositiveValues,
                validators.ValidateSampleDepth,
                validators.ValidateSecchiDepth,
                validators.ValidateSerialNumber,
                validators.ValidateSpeed,
                validators.ValidateStationIdentity,
                validators.ValidateSynonymsInMaster,
                validators.ValidateWindir,
                validators.ValidateWinsp,
            )
        }

        for row in adm_logger.data:
            validator_name = row["validator"]
            if row.get("validation_success"):
                validation_remarks[validator_name]["success"][
                    row.get("column") or "General"
                ].append(row["msg"])
            else:
                validation_remarks[validator_name]["fail"][
                    row.get("column") or "General"
                ].append(row["msg"])

        for validator, remarks in validation_remarks.items():
            remarks["success_count"] = sum(
                len(column) for column in remarks["success"].values()
            )
            remarks["fail_count"] = sum(
                len(column) for column in remarks["fail"].values()
            )

            remarks["description"] = description_for_validator.get(validator, "")

        return validation_remarks

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
            int(manual_flag)
        except ValueError:
            return qflag_str

        q.manual = QcFlag(int(manual_flag))

        return str(q)

    def apply_feedback_file(self, raw_data: pl.DataFrame, feedback_data: pl.DataFrame):
        print("applying manual flags from feedback file....")
        join_columns = ["visit_key", "DEPH", "parameter"]
        # Join feedback into raw data
        joined_data = raw_data.join(
            feedback_data, on=join_columns, how="left", suffix="_feedback"
        )
        joined_data = joined_data.with_columns(
            pl.when(
                (pl.col("MANUAL_QC") != pl.col("MANUAL_QC_feedback"))
                & pl.col("MANUAL_QC_feedback").is_not_null()
            )
            .then(
                pl.struct(["quality_flag_long", "MANUAL_QC_feedback"]).map_elements(
                    lambda row: self._apply_manual_flag(
                        row["quality_flag_long"], row["MANUAL_QC_feedback"]
                    ),
                    return_dtype=pl.Utf8,
                )
            )
            .otherwise(pl.col("quality_flag_long"))
            .alias("quality_flag_long"),
            pl.when(
                (pl.col("MANUAL_QC") != pl.col("MANUAL_QC_feedback"))
                & pl.col("MANUAL_QC_feedback").is_not_null()
            )
            .then(pl.col("MANUAL_QC_feedback"))
            .otherwise(pl.col("MANUAL_QC"))
            .alias("MANUAL_QC"),
        )
        print("data updated with manual flags from feedback file")
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
