import calendar
import typing

from qc_tool.models.filter_model import FilterModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.filter_controller import FilterController

from bokeh.models import Button, MultiChoice, Row

from qc_tool.data_transformation import shortest_unique_paths
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

MISSING_LABEL = "Missing value"


class FilterView(BaseView):
    HEIGHT = 150

    def __init__(self, controller: "FilterController", filter_model: FilterModel):
        self._controller = controller
        self._controller.filter_view = self

        self._filter_model = filter_model

        common_config = {
            "min_width": 200,
        }

        self._file_filter = MultiChoice(
            title="File",
            **common_config,
        )
        self._file_filter.on_change("value", self._on_file_filter_changed)

        self._year_filter = MultiChoice(
            title="Year",
            **common_config,
        )
        self._year_filter.on_change("value", self._on_year_filter_changed)

        self._month_filter = MultiChoice(title="Month", **common_config)
        self._month_filter.on_change("value", self._on_month_filter_changed)

        self._cruise_filter = MultiChoice(title="Cruise", **common_config)
        self._cruise_filter.on_change("value", self._on_cruise_filter_changed)

        self._basin_filter = MultiChoice(title="Basin", **common_config)
        self._basin_filter.on_change("value", self._on_basin_filter_changed)

        self._station_filter = MultiChoice(title="Station", **common_config)
        self._station_filter.on_change("value", self._on_station_filter_changed)

        self._clear_filter_button = Button(
            label="Clear", width=100, sizing_mode="scale_width"
        )
        self._clear_filter_button.on_click(self.clear_filter)

        self._layout = Row(
            children=[
                self._clear_filter_button,
                self._file_filter,
                self._year_filter,
                self._month_filter,
                self._cruise_filter,
                self._basin_filter,
                self._station_filter,
            ],
            max_height=self.HEIGHT,
        )

    def _on_file_filter_changed(self, attr, old, new):
        self._filter_model.set_file_filter(new)

    def _on_year_filter_changed(self, attr, old, new):
        values = {None if value == MISSING_LABEL else int(value) for value in new}
        self._filter_model.set_year_filter(values)

    def _on_month_filter_changed(self, attr, old, new):
        values = {None if value == "None" else int(value) for value in new}
        self._filter_model.set_month_filter(values)

    def _on_cruise_filter_changed(self, attr, old, new):
        values = {"" if value == MISSING_LABEL else value for value in new}
        self._filter_model.set_cruise_filter(values)

    def _on_station_filter_changed(self, attr, old, new):
        values = {"" if value == MISSING_LABEL else value for value in new}
        self._filter_model.set_station_filter(values)

    def _on_basin_filter_changed(self, attr, old, new):
        values = {None if value == MISSING_LABEL else value for value in new}
        self._filter_model.set_basin_filter(values)

    def clear_filter(self, event):
        self._file_filter.value = []
        self._year_filter.value = []
        self._month_filter.value = []
        self._cruise_filter.value = []
        self._basin_filter.value = []
        self._station_filter.value = []

    @property
    def layout(self):
        return self._layout

    def update_filter_options(self):
        all_paths = self._filter_model.file_paths
        short_names = shortest_unique_paths(all_paths)
        available = set(self._filter_model.files)
        self._file_filter.options = [
            (str(path), short_names[path]) for path in all_paths if str(path) in available
        ]
        self._year_filter.options = [
            MISSING_LABEL if year is None else str(year)
            for year in self._filter_model.years
        ]
        self._month_filter.options = [
            (
                str(month) if month is not None else "None",
                calendar.month_abbr[month] if month is not None else MISSING_LABEL,
            )
            for month in self._filter_model.months
        ]
        self._cruise_filter.options = [
            MISSING_LABEL if cruise == "" else str(cruise)
            for cruise in self._filter_model.cruises
        ]
        self._station_filter.options = [
            MISSING_LABEL if station == "" else station
            for station in self._filter_model.stations
        ]
        self._basin_filter.options = [
            MISSING_LABEL if basin is None else basin
            for basin in self._filter_model.basins
        ]
