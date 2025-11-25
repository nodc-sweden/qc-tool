from pathlib import Path

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
            self._state.file,
            self._state.visits,
            self._state.filter,
        )

        self._transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")

        self.filter_controller = FilterController(self._state.visits, self._state.filter)

        self.summary_controller = SummaryController(
            self._state.file,
            self._state.visits,
            self._state.map,
            self._state.validation_log,
            self._state.manual_qc,
            self._state.geo_info,
        )
        self.visits_browser_controller = VisitsBrowserController(self._state)

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

    def _convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes
