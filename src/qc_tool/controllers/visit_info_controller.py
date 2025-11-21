from collections import defaultdict

from ocean_data_qc.metadata.metadata_flag import MetadataFlag

from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.visit_info_view import VisitInfoView

_class_from_status = {
    MetadataFlag.NO_QC_PERFORMED: "no-qc-performed",
    MetadataFlag.GOOD_DATA: "good-data",
    MetadataFlag.BAD_DATA: "bad-data",
}


class VisitInfoController:
    STATION_DATA_FIELDS = (
        ("STATN", "Station name"),
        ("SERNO", "Series"),
        ("CTRYID+SHIPC+CRUISE_NO", "Country-Ship-Cruise"),
        ("SDATE+STIME", "Time"),
        ("WADEP", "Water depth"),
        ("AIRTEMP", "Air temperature"),
        ("AIRPRES", "Air pressure"),
        ("WINDIR", "Wind direction"),
        ("WINSP", "Wind speed"),
        ("COMNT_VISIT", "Comment"),
        ("COMNT_INTERN", "Internal comment"),
        ("LATIT", "Latitude"),
        ("LONGI", "Longitude"),
    )

    def __init__(self, visits_model: VisitsModel):
        self._visits_model = visits_model
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._on_visit_selected
        )

        self.visit_info_view: VisitInfoView = None

    def _on_visit_selected(self):
        if visit := self._visits_model.selected_visit:
            checks_per_field = defaultdict(set)
            for check, fields in visit.metadata.qc_log.items():
                for field in fields:
                    checks_per_field[field].add(check)

            status_per_field = {
                field: max(visit.metadata.qc[check] for check in checks)
                for field, checks in checks_per_field.items()
            }

            metadata = [
                (
                    header,
                    visit.common.get(key, ""),
                    _class_from_status[
                        max(
                            status_per_field.get(sub_key, MetadataFlag.NO_QC_PERFORMED)
                            for sub_key in key.split("+")
                        )
                    ],
                )
                for key, header in self.STATION_DATA_FIELDS
            ]
        else:
            metadata = [
                (header, "", "no-qc-performed") for _, header in self.STATION_DATA_FIELDS
            ]

        self.visit_info_view.update(metadata)
