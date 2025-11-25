import os
import time
import tkinter
import tkinter.filedialog
from collections import defaultdict
from pathlib import Path

import geopandas as gp
import nodc_station
from bokeh.io import curdoc
from bokeh.models import Button, Column, Div, FileInput, ImportedStyleSheet
from sharkadm import adm_logger, exporters, multi_transformers, transformers, validators
from sharkadm import controller as sharkadm_controller

from qc_tool.views.base_view import BaseView

CONFIG_ENV = "NODC_CONFIG"

_home = Path.home()
OTHER_CONFIG_SOURCES = [
    _home / "NODC_CONFIG",
    _home / ".NODC_CONFIG",
    _home / "nodc_config",
    _home / ".nodc_config",
]


def _get_config_dir() -> Path | None:
    if config_dir := os.getenv(CONFIG_ENV):
        return Path(config_dir)
    for config_dir in OTHER_CONFIG_SOURCES:
        if config_dir.exists():
            return config_dir
    return None


def _load_ocean_shapefile():
    if _config_dir := _get_config_dir():
        shapefile = (
            _config_dir / "sharkweb_shapefiles" / "Havsomr_SVAR_2016_3c_CP1252.shp"
        )
        if shapefile.exists():
            return gp.read_file(shapefile)
    return gp.GeoDataFrame()


class FileHandler(BaseView):
    def __init__(
        self,
        external_load_file_callback,
        external_save_file_callback,
        external_save_changes_file_callback,
        external_automatic_qc_callback,
    ):
        self._file_name = None

        self._external_load_file_callback = external_load_file_callback
        self._external_save_file_callback = external_save_file_callback
        self._external_save_changes_file_callback = external_save_changes_file_callback
        self._external_automatic_qc_callback = external_automatic_qc_callback

        self._load_header = Div(width=500, text="<h3>Load and save</h3>")
        self._loaded_file_label = Div(width=500)

        self._file_input = FileInput(
            title="Select file:", accept=".txt,.csv", max_width=500
        )

        self._file_button = Button(label="Select data...")
        self._file_button.on_click(self._load_file)

        self._save_as_button = Button(label="Save as...")
        self._save_as_button.on_click(
            lambda: self._save_file_as_callback(self._external_save_file_callback)
        )

        self._save_changes_as_button = Button(label="Save only changed rows as...")
        self._save_changes_as_button.on_click(
            lambda: self._save_file_as_callback(
                self._external_save_changes_file_callback, file_type="xlsx"
            )
        )

        self._load_indicator = Div(
            width=120,
            height=120,
            text='<div class="loader"></div>',
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
        )
        self._load_indicator.visible = False

        self._file_loaded()

    def _load_file(self, event):
        try:
            root = tkinter.Tk()
            root.iconify()
            selected_path = tkinter.filedialog.askopenfilename()
            root.destroy()
        except tkinter.TclError:
            selected_path = None

        if not selected_path:
            return
        selected_path = Path(selected_path)
        print(f"Load data from {selected_path}...")
        self._load_indicator.visible = True
        curdoc().add_next_tick_callback(lambda: self._load_file_callback(selected_path))

    def _load_file_callback(self, selected_path: Path):
        controller = sharkadm_controller.get_polars_controller_with_data(selected_path)

        self._reset_validation_logs()
        self._apply_transformers(controller)
        self._run_validators(controller)
        validation = self._collect_validation_logs()
        print("Data loaded")
        data = controller.export(
            exporters.PolarsDataFrame(header_as="PhysicalChemical", float_columns=True)
        )

        self._file_name = selected_path.name
        self._file_loaded()
        self._external_load_file_callback(data, validation)
        self._external_automatic_qc_callback()

        self._load_indicator.visible = False

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

    def _reset_validation_logs(self):
        adm_logger.reset_log()

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

    def _file_loaded(self):
        if self._file_name:
            file_info = f"<p>{self._file_name}</p>"
        else:
            file_info = "<p>No file loaded</p>"
        self._loaded_file_label.text = file_info

    def _save_file_as_callback(self, save_file_callback, file_type: str = "txt"):
        try:
            root = tkinter.Tk()
            root.iconify()
            if file_type == "txt":
                filetypes = [("Text Files", "*.txt"), ("All Files", "*.*")]
                default_extension = ".txt"
            elif file_type == "xlsx":
                filetypes = [("Excel Files", "*.xlsx"), ("All Files", "*.*")]
                default_extension = ".xlsx"
            else:
                filetypes = [("All Files", "*.*")]
                default_extension = ""
            selected_path = tkinter.filedialog.asksaveasfilename(
                defaultextension=default_extension,
                filetypes=filetypes,
            )
            root.destroy()
        except tkinter.TclError:
            selected_path = None

        if not selected_path:
            return
        selected_path = Path(selected_path)
        save_file_callback(selected_path)

    @property
    def layout(self):
        return Column(
            self._load_header,
            self._file_button,
            self._loaded_file_label,
            self._save_as_button,
            self._save_changes_as_button,
            self._load_indicator,
        )
