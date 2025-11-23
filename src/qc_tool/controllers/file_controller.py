import os
import time
from collections import defaultdict
from pathlib import Path

import geopandas
import nodc_station
import polars as pl
from nodc_statistics import regions
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

from qc_tool.data_transformation import prepare_data
from qc_tool.models.file_model import FileModel
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
    def __init__(self, file_model: FileModel, validation_log_model: ValidationLogModel):
        self._file_model = file_model
        self._file_model.register_listener(FileModel.NEW_DATA, self._new_file)
        self._file_model.register_listener(FileModel.LOAD_ABORTED, self._load_aborted)

        self._validation_log_model = validation_log_model

        self.file_view = None
        self._geo_info = None

    @property
    def file_model(self):
        return self._file_model

    def load_file(self, file_path):
        print(f"Loading data from {file_path}...")
        data = pl.read_csv(
            file_path,
            separator="\t",
            dtypes={
                "sea_basin": pl.Utf8,
                "LONGI_NOM": pl.Utf8,
                "LATIT_NOM": pl.Utf8,
                "datetime": pl.Datetime,
            },
        )
        self._set_data(data, file_path)
        #self._validation_log_model.set_validation_log(validation_log)


    def load_file_2(self, file_path):
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
        validation_log = self._collect_validation_logs()
        print("Data loaded")
        data = controller.export(
            exporters.PolarsDataFrame(header_as="PhysicalChemical", float_columns=True)
        )
        data = self._match_sea_basins(data)
        data = prepare_data(data)
        self._set_data(data, file_path)
        self._validation_log_model.set_validation_log(validation_log)

    def _new_file(self):
        self.file_view._file_load_completed()

    def _load_aborted(self):
        self.file_view._file_load_completed()

    def _reset_validation_logs(self):
        adm_logger.reset_log()

    def _apply_transformers(self, controller):
        print("Running SHARKadm transformers...")
        t0 = time.perf_counter()
        for transformer, args, kwargs in (
            (transformers.PolarsRemoveNonDataLines, (), {}),
            (transformers.PolarsReplaceCommaWithDot, (), {}),
            (multi_transformers.DateTimePolars, (), {}),
            (multi_transformers.PositionPolars, (), {}),
            (transformers.PolarsAddVisitKey, (), {}),
            (transformers.PolarsWideToLong, (), {}),
            (transformers.PolarsMoveLessThanFlagRowFormat, (), {}),
            (transformers.PolarsMoveLargerThanFlagRowFormat, (), {}),
            (transformers.PolarsConvertFlagsToSDN, (), {}),
            (transformers.PolarsAddPressure, (), {}),
            (transformers.PolarsAddDensity, (), {}),
            (transformers.PolarsAddOxygenSaturation, (), {}),
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
                validators.ValidateCommonValuesByVisit,
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

    def _automatic_qc_callback(self, event):
        self._external_automatic_qc_callback()

    def _set_data(self, data: pl.DataFrame, file_path: Path):
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

            self._file_model.add_data(
                data.with_columns(split).unnest("split_qc_fields"), file_path
            )
        else:
            self._file_model.add_data(data, file_path)

        # self._set_stations(stations)
        # self._station_navigator.load_stations(self._stations)
        # self._parameter_handler.reset_selection()
        # self.set_station(station or station_visit[0])


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
