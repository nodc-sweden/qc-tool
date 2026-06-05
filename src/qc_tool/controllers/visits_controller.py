import re

import polars as pl

from qc_tool.feedback_service import FeedbackService
from qc_tool.models.ctd_file_model import CtdFileModel
from qc_tool.models.file_model import FileModel
from qc_tool.models.filter_model import FilterModel
from qc_tool.models.validation_log_model import ValidationLogModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.visit import Visit

GEOLAYERS_AREATAG = {
    "SVAR2022_typomrkust_lagad": "TYPOMRKUST",
    "ospar_subregions_20160418_3857_lagad": "area_tag",
    "helcom_subbasins_with_coastal_and_offshore_division_2022_level3_lagad": "level_34",
}

VISIT_KEY_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{2}:\d{2})_(\d+)_(.*)")


def _normalized_visit_key(visit_key: str) -> str:
    """This is a temporary method to normalize visit keys good enough for matching
    LIMS and CTD."""
    if match := VISIT_KEY_PATTERN.match(visit_key):
        return f"{match.group(1)}_{match.group(3)}_{match.group(4)}".lower()
    return visit_key.lower()


class VisitsController:
    def __init__(
        self,
        file_model: FileModel,
        ctd_file_model: CtdFileModel,
        visits_model: VisitsModel,
        filter_model: FilterModel,
        validation_log_model: ValidationLogModel,
    ):
        self._file_model = file_model
        self._ctd_file_model = ctd_file_model
        self._visits_model = visits_model
        self._validation_log_model = validation_log_model
        self._file_model.register_listener(FileModel.NEW_DATA, self._on_new_data)
        self._ctd_file_model.register_listener(
            CtdFileModel.NEW_DATA, self._on_updated_data
        )
        self._file_model.register_listener(FileModel.UPDATED_DATA, self._on_updated_data)
        self._file_model.register_listener(
            FileModel.NEW_MANUAL_FLAGS, self._on_new_manual_flags
        )
        self._visits_model.register_listener(VisitsModel.NEW_VISITS, self._on_new_visits)
        self._filter_model = filter_model
        self._filter_model.register_listener(
            FilterModel.FILTER_CHANGED, self._on_filter_changed
        )
        self._visits_model.register_listener(
            VisitsModel.NEW_VISITS, self._build_feedback_service
        )
        self._validation_log_model.register_listener(
            validation_log_model.NEW_VALIDATION_LOG, self._on_new_validation_log
        )
        self._visits_model.register_listener(
            VisitsModel.UPDATED_VISITS, self._build_feedback_service
        )

    def _on_new_data(self):
        visits = self._create_visits()
        self._visits_model.set_visits(visits)
        self._build_feedback_service()

    def _on_updated_data(self):
        visits = self._create_visits()
        self._visits_model.update_visits(visits)
        self._build_feedback_service()

    def _create_visits(self):
        # Extract list of all station visits
        station_visits = sorted(self._file_model.data["visit_key"].unique())

        # Initialize all visits
        visits = {
            visit_key: Visit(
                visit_key,
                self._file_model.data.filter(pl.col("visit_key") == visit_key),
                self._ctd_file_model.data.filter(
                    pl.col("visit_key").map_elements(
                        _normalized_visit_key, return_dtype=pl.Utf8
                    )
                    == _normalized_visit_key(visit_key)
                )
                if self._ctd_file_model.data is not None
                else None,
            )
            for visit_key in station_visits
        }

        return visits

    def _on_new_visits(self):
        self._visits_model.set_visit(self._visits_model.first_visit_or_none())

    def _on_filter_changed(self):
        self._visits_model.apply_filter(self._filter_model)

    def _on_new_manual_flags(self):
        visit_key = self._visits_model.selected_visit.visit_key
        visit = self._update_visit(visit_key)
        self._visits_model.update_visit(visit_key, visit)
        self._build_feedback_service()

    def _update_visit(self, visit_key: str | None):
        if visit_key is None:
            return self._visits_model.visits
        visit = Visit(
            visit_key, self._file_model.data.filter(pl.col("visit_key") == visit_key)
        )
        return visit

    def _on_new_validation_log(self):
        self._build_feedback_service()

    def _build_feedback_service(self):
        self._feedback_service = FeedbackService(
            validation_log=self._validation_log_model.validation_log,
            visits_model=self._visits_model,
        )

        self._attach_logs_to_visits()

    def _attach_logs_to_visits(self):
        if not self._feedback_service:
            return

        for visit in self._visits_model.visits.values():
            visit.validation_logs = self._feedback_service.get_logs_for_visit(visit)

        self._visits_model._notify_listeners(VisitsModel.FEEDBACK_READY)
