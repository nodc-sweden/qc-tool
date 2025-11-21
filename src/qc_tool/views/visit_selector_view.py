import typing

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
        width: int = 400,
    ):
        self._controller = controller
        controller.visit_selector_view = self

        self._visits_model = visits_model

        self._previous_button = Button(label="<")
        self._previous_button.on_event("button_click", self._previous_button_clicked)

        self._next_button = Button(label=">")
        self._next_button.on_event("button_click", self._next_button_clicked)

        self._visits_dropdown = Dropdown(
            label="Select visit",
            button_type="default",
            min_width=300,
            max_width=width,
            menu=self._visits_model.visit_keys,
        )
        self._visits_dropdown.on_click(self._visit_dropdown_changed)
        self._layout = Row(
            self._previous_button,
            self._visits_dropdown,
            self._next_button,
            width=width,
        )

    def _visit_dropdown_changed(self, event):
        station_visit = event.item
        self._controller.set_visit(station_visit)

    def _previous_button_clicked(self):
        station_index = (
            self._visits_dropdown.menu.index(self._visits_dropdown.label) - 1
        ) % len(self._visits_dropdown.menu)
        station_visit = self._visits_dropdown.menu[station_index]
        self._controller.set_visit(station_visit)

    def _next_button_clicked(self):
        station_index = (
            self._visits_dropdown.menu.index(self._visits_dropdown.label) + 1
        ) % len(self._visits_dropdown.menu)
        station_visit = self._visits_dropdown.menu[station_index]
        self._controller.set_visit(station_visit)

    def update_visits(self):
        self._visits_dropdown.menu = self._visits_model.visit_keys

    @property
    def layout(self):
        return self._layout

    def set_visit(self, station_visit: str):
        self._visits_dropdown.label = station_visit
