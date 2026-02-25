from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.visit_info_view import VisitInfoView


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
            metadata = [
                (
                    header,
                    visit.common.get(key, ""),
                )
                for key, header in self.STATION_DATA_FIELDS
            ]
        else:
            metadata = [(header, "") for _, header in self.STATION_DATA_FIELDS]

        self.visit_info_view.update(metadata)
