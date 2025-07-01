import os
import time
import tkinter
import tkinter.filedialog
from collections import defaultdict
from pathlib import Path
from typing import Any

import geopandas as gp
import pandas as pd
from bokeh.models import Button, Column, Div, FileInput
from sharkadm import adm_logger, exporters, multi_transformers, transformers
from sharkadm import controller as sharkadm_controller
from sharkadm.validators import ValidateCommonValuesByVisit, ValidatePositiveValues
from sharkadm.validators.station import (
    ValidateCoordinatesDm,
    ValidateNameInMaster,
    ValidatePositionInOcean,
    ValidatePositionWithinStationRadius,
    ValidateStationIdentity,
    ValidateSynonymsInMaster,
)

from qc_tool.layoutable import Layoutable


def get_config_dir() -> Path | None:
    if dir_from_env := os.getenv("NODC_CONFIG"):
        conf_dir = Path(dir_from_env)
        if conf_dir.exists():
            return conf_dir

    dir_in_home = Path.home() / "SHARKadmConfig"
    if dir_in_home.exists():
        return dir_in_home


def load_station_info() -> dict[str, Any]:
    stations = {}
    if _config_dir := get_config_dir():
        stations_file = _config_dir / "station.txt"
        if stations_file.exists():
            stations_data = pd.read_csv(
                stations_file, encoding="cp1252", sep="\t"
            ).fillna("")

            # Split synonyms on "<or>". All entries become lists
            stations_data.SYNONYM_NAMES = stations_data.SYNONYM_NAMES.apply(
                lambda x: x.split("<or>") if x else []
            )

            # Create a dictionary from station name to list of synonyms
            stations = {
                station_name: {
                    "synonyms": synonyms,
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius": radius,
                }
                for station_name, synonyms, latitude, longitude, radius in zip(
                    stations_data.STATION_NAME,
                    stations_data.SYNONYM_NAMES,
                    stations_data.LATITUDE_SWEREF99TM,
                    stations_data.LONGITUDE_SWEREF99TM,
                    stations_data.OUT_OF_BOUNDS_RADIUS,
                )
            }
    return stations


def load_ocean_shapefile():
    if _config_dir := get_config_dir():
        shapefile = (
            _config_dir / "sharkweb_shapefiles" / "Havsomr_SVAR_2016_3c_CP1252.shp"
        )
        if shapefile.exists():
            return gp.read_file(shapefile)
    return gp.GeoDataFrame()


class FileHandler(Layoutable):
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
        self._file_button.on_click(self._load_file_callback)

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

        self._file_loaded()

    def _load_file_callback(self, event):
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
        controller = sharkadm_controller.get_controller_with_data(selected_path)
        self._apply_transformers(controller=controller)
        self._run_validators(controller)
        validation = self._collect_validation_log()
        print("Data loaded")
        data = controller.export(
            exporters.DataFrame(header_as="PhysicalChemical", float_columns=True)
        )
        self._file_name = selected_path.name
        self._file_loaded()
        self._external_load_file_callback(data, validation)
        self._external_automatic_qc_callback()

    def _apply_transformers(self, controller):
        controller.transform(transformers.RemoveNonDataLines())
        controller.transform(transformers.WideToLong())
        controller.transform(transformers.ReplaceCommaWithDot())
        controller.transform(transformers.AddSampleDate())
        controller.transform(transformers.AddSampleTime())
        controller.transform(transformers.AddDatetime())
        controller.transform(transformers.AddMonth())
        controller.transform(transformers.AddVisitKey())
        controller.transform(transformers.AddAnalyseInfo())

        controller.transform(multi_transformers.Position())

        controller.transform(transformers.MoveLessThanFlagRowFormat())
        controller.transform(transformers.MoveLargerThanFlagRowFormat())
        controller.transform(transformers.ConvertFlagsToSDN())
        controller.transform(transformers.RemoveColumns("COPY_VARIABLE.*"))
        controller.transform(
            transformers.MapperParameterColumn(import_column="SHARKarchive")
        )

    def _run_validators(self, controller):
        print("Running SHARKadm validators...")
        t0 = time.perf_counter()

        stations_info = load_station_info()
        ocean_shapefile = load_ocean_shapefile()

        validators_and_parameters = (
            (ValidateCommonValuesByVisit, {}),
            (ValidatePositiveValues, {}),
            (
                ValidateStationIdentity,
                {
                    "stations": [
                        (
                            key,
                            value["synonyms"],
                            value["longitude"],
                            value["latitude"],
                            value["radius"],
                        )
                        for key, value in stations_info.items()
                    ],
                    "station_name_key": "reported_station_name",
                    "latitude_key": "sample_sweref99tm_y",
                    "longitude_key": "sample_sweref99tm_x",
                },
            ),
            (
                ValidateNameInMaster,
                {
                    "station_names": set(stations_info.keys()),
                    "station_name_column": "reported_station_name",
                },
            ),
            (
                ValidateSynonymsInMaster,
                {
                    "station_aliases": {
                        key: value["synonyms"] for key, value in stations_info.items()
                    },
                    "station_name_column": "reported_station_name",
                },
            ),
            (
                ValidateCoordinatesDm,
                {
                    "latitude_dm_column": "visit_reported_latitude",
                    "longitude_dm_column": "visit_reported_longitude",
                },
            ),
            (
                ValidatePositionInOcean,
                {
                    "ocean_shapefile": ocean_shapefile,
                    "station_name_key": "reported_station_name",
                    "latitude_key": "sample_sweref99tm_y",
                    "longitude_key": "sample_sweref99tm_x",
                },
            ),
            (
                ValidatePositionWithinStationRadius,
                {
                    "stations": [
                        (key, value["longitude"], value["latitude"], value["radius"])
                        for key, value in stations_info.items()
                    ],
                    "station_name_key": "reported_station_name",
                    "latitude_key": "sample_sweref99tm_y",
                    "longitude_key": "sample_sweref99tm_x",
                },
            ),
        )
        for validator, parameters in validators_and_parameters:
            validator(**parameters).validate(controller.data_holder)

        t1 = time.perf_counter()
        print(f"SHARKadm validators finished ({t1 - t0:.3f} s.)")

    def _collect_validation_log(self):
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
                ValidateCommonValuesByVisit,
                ValidateCoordinatesDm,
                ValidateNameInMaster,
                ValidatePositionInOcean,
                ValidatePositionWithinStationRadius,
                ValidatePositiveValues,
                ValidateStationIdentity,
                ValidateSynonymsInMaster,
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
        )
