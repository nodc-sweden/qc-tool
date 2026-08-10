import typing

from qc_tool.models.filter_model import FilterModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.visit_selector_controller import VisitSelectorController

from bokeh.models import Button, Dropdown, Row

from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.base_view import BaseView


class VisitSelectorView(BaseView):
    def __init__(
        self,
        controller: "VisitSelectorController",
        visits_model: VisitsModel,
        filter_model: FilterModel,
        width: int = 400,
    ):
        self._controller = controller
        controller.visit_selector_view = self

        self._visits_model = visits_model
        self._filter_model = filter_model

        self._previous_button = Button(label="<")
        self._previous_button.on_event("button_click", self._on_previous_button_clicked)

        self._next_button = Button(label=">")
        self._next_button.on_event("button_click", self._on_next_button_clicked)

        self._visits_dropdown = Dropdown(
            label="Select visit",
            button_type="default",
            min_width=300,
            max_width=width,
            menu=self._visit_menu(),
        )
        self._visits_dropdown.on_click(self._on_visit_dropdown_changed)
        self._layout = Row(
            self._previous_button,
            self._visits_dropdown,
            self._next_button,
            width=width,
        )

    def _on_visit_dropdown_changed(self, event):
        station_visit = event.item
        self._controller.set_visit(station_visit)

    def _on_previous_button_clicked(self):
        self._controller.set_visit(self._visits_model.previous_visit_key())

    def _on_next_button_clicked(self):
        self._controller.set_visit(self._visits_model.next_visit_key())

    def _visit_menu(self):
        return list(
            zip(
                self._visits_model.visit_labels,
                self._visits_model.visit_keys,
            )
        )

    def update_visits(self):
        self._visits_dropdown.menu = self._visit_menu()

    @property
    def layout(self):
        return self._layout

    def set_visit(self, station_visit: str | None):
        if station_visit is None:
            self._visits_dropdown.label = "Select visit"
        else:
            self._visits_dropdown.label = self._visits_model.visit_label_by_key.get(
                station_visit,
                station_visit,
            )
