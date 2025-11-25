import polars as pl

from qc_tool.models.file_model import FileModel
from qc_tool.models.filter_model import FilterModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.visit import Visit

GEOLAYERS_AREATAG = {
    "SVAR2022_typomrkust_lagad": "TYPOMRKUST",
    "ospar_subregions_20160418_3857_lagad": "area_tag",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3_lagad": "level_34",
}


class VisitsController:
    def __init__(
        self, file_model: FileModel, visits_model: VisitsModel, filter_model: FilterModel
    ):
        self._file_model = file_model
        self._visits_model = visits_model
        self._file_model.register_listener(FileModel.NEW_DATA, self._on_new_data)
        self._file_model.register_listener(FileModel.UPDATED_DATA, self._on_updated_data)
        self._visits_model.register_listener(VisitsModel.NEW_VISITS, self._on_new_visits)
        self._filter_model = filter_model
        self._filter_model.register_listener(
            FilterModel.FILTER_CHANGED, self._on_filter_changed
        )

    def _on_new_data(self):
        visits = self._create_visits()
        self._visits_model.set_visits(visits)

    def _on_updated_data(self):
        visits = self._create_visits()
        self._visits_model.update_visits(visits)

    def _create_visits(self):
        # Extract list of all station visits
        station_visit = sorted(self._file_model.data["visit_key"].unique())

        # Initialize all visits
        visits = {
            visit_key: Visit(
                visit_key,
                self._file_model.data.filter(pl.col("visit_key") == visit_key),
            )
            for visit_key in station_visit
        }
        return visits

    def _on_new_visits(self):
        self._visits_model.set_visit(self._visits_model.first_visit_or_none())

    def _on_filter_changed(self):
        self._visits_model.apply_filter(self._filter_model)
