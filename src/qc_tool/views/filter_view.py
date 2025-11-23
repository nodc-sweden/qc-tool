import typing

from qc_tool.models.filter_model import FilterModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.filter_controller import FilterController
from bokeh.models import Button, MultiChoice, Row

from qc_tool.views.base_view import BaseView

MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


class FilterView(BaseView):
    HEIGHT = 150

    def __init__(self, controller: "FilterController", filter_model: FilterModel):
        self._controller = controller
        self._controller.filter_view = self

        self._filter_model = filter_model

        common_config = {
            "min_width": 200,
        }

        self._year_filter = MultiChoice(
            title="Year",
            value=[],
            options=list(map(str, range(2000, 2026))),
            **common_config,
        )

        self._month_filter = MultiChoice(
            title="Month", value=[], options=MONTHS, **common_config
        )
        self._month_filter.on_change("value", self._on_month_filter_changed)

        self._cruise_filter = MultiChoice(
            title="Cruise", value=[], options=[], **common_config
        )

        self._station_filter = MultiChoice(
            title="Station", value=[], options=[], **common_config
        )
        self._station_filter.on_change("value", self._on_station_filter_changed)

        self._clear_filter_button = Button(
            label="Clear", width=100, sizing_mode="scale_width"
        )
        self._clear_filter_button.on_click(self.clear_filter)

        self._layout = Row(
            children=[
                self._clear_filter_button,
                self._year_filter,
                self._month_filter,
                self._cruise_filter,
                self._station_filter,
            ],
            max_height=self.HEIGHT,
        )

    def _on_month_filter_changed(self, attr, old, new):
        self._filter_model.set_month_filter(new)

    def _on_year_filter_changed(self, attr, old, new):
        print("Year filter changed")

    def _on_cruise_filter_changed(self, attr, old, new):
        print("Cruise filter changed")

    def _on_station_filter_changed(self, attr, old, new):
        self._filter_model.set_station_filter(new)

    def clear_filter(self, event):
        self._year_filter.value = []
        self._month_filter.value = []
        self._cruise_filter.value = []
        self._station_filter.value = []

    @property
    def layout(self):
        return self._layout

    def update_filter_options(self):
        self._year_filter.options = [str(year) for year in self._filter_model.years]
        self._month_filter.options = [(str(month), MONTHS[month]) for month in self._filter_model.months]
        self._cruise_filter.options = [str(cruise) for cruise in self._filter_model.cruises]
        self._station_filter.options = self._filter_model.stations
