import numpy as np
from bokeh.core.property.primitive import Bool
from bokeh.layouts import column
from bokeh.model import DataModel
from bokeh.models import (
    BoxAnnotation,
    CheckboxButtonGroup,
    ColumnDataSource,
    Dropdown,
    WheelZoomTool,
)
from bokeh.plotting import figure

from qc_tool.station import Station

PARAMETER_ABBREVIATIONS = {
    "ALKY": "Alkalinity",
    "AMON": "Ammonium",
    "CHLFL": "Chlorophyll-a fluorescence",
    "CPHL": "Chlorophyll-a",
    "DEPTH_CTD": "Depth (CTD)",
    "DOXY_BTL": "Oxygen (bottle)",
    "DOXY_CTD": "Oxygen (CTD)",
    "DOXY_CTD_2": "Oxygen (CTD) 2",
    "H2S": "Hydrogen sulfide",
    "HUMUS": "Humus",
    "NTOT": "Total nitrogen",
    "NTRA": "Nitrate",
    "NTRI": "Nitrite",
    "NTRZ": "Nitrate + Nitrite",
    "PH": "pH",
    "PHOS": "Phosphate",
    "PH_LAB": "pH Laboratory",
    "PH_LAB_TEMP": "Temperature pH Laboratory",
    "PTOT": "Total phosphorus",
    "SALT_BTL": "Salinity (bottle)",
    "SALT_CTD": "Salinity (CTD)",
    "SALT_CTD_2": "Salinity (CTD) 2",
    "SECCHI": "Secchi depth",
    "SIO3-SI": "Silicate",
    "TEMP_BTL": "Temperature (bottle)",
    "TEMP_CTD": "Temperature (CTD)",
    "TEMP_CTD_2": "Temperature (CTD) 2",
}


def expand_abbreviation(abbreviation: str) -> str:
    return PARAMETER_ABBREVIATIONS.get(abbreviation, abbreviation)


class ParameterSlot:
    def __init__(
        self,
        parameter: str = None,
        linked_y_range=None,
        default_parameter: str = None,
    ):
        self._default_parameter = default_parameter
        self._parameter = parameter or self._default_parameter
        self._station = None
        self._source = ColumnDataSource(data={"x": [], "y": []})

        self._parameter_options = ParameterOptions()

        wheel_zoom = WheelZoomTool()
        self._figure_config = {
            "height": 500,
            "width": 500,
            "toolbar_location": "below",
            "tools": ["pan", wheel_zoom, "reset"],
        }

        self._plot_config = {
            "size": 7,
            "color": "navy",
            "alpha": 0.8,
        }

        self._figure = figure(**self._figure_config)
        self._figure.toolbar.active_scroll = wheel_zoom

        # Add sea level abd sky
        self._sky = self._figure.image_url(
            url=["qc_tool/static/images/gull.png"], x=0, y=-500
        )
        self._sea_level = BoxAnnotation(
            bottom=0, fill_color="lightskyblue", fill_alpha=0.10
        )
        self._sea_level.level = "underlay"
        self._figure.add_layout(self._sea_level)

        # Add ocean floor
        self._ocean_floor = BoxAnnotation(fill_color="saddlebrown", fill_alpha=0.75)
        self._ocean_floor.level = "underlay"
        self._figure.add_layout(self._ocean_floor)

        # Add points and lines
        self._lines = self._figure.line("x", "y", source=self._source, line_width=1)
        self._figure.scatter("x", "y", source=self._source, **self._plot_config)
        if linked_y_range:
            self._figure.y_range = linked_y_range
        else:
            self._figure.y_range.flipped = True

        # Add parameter selector
        self._parameter_dropdown = Dropdown(
            label=expand_abbreviation(self._parameter) or "Parameter",
            button_type="default",
            menu=[],
            name="parameter",
            width=200,
        )
        self._parameter_dropdown.on_click(self.parameter_selected)

        # Add checkbox to toggle lines
        self._parameter_options_checkbox = CheckboxButtonGroup(labels=["Lines", "Bounds"])
        self._parameter_options_checkbox.on_change(
            "active", self._toggle_parameter_options
        )

        self._sync_parameter_options()

    def update_station(self, station: Station):
        self._station = station
        self._parameter_dropdown.menu = [
            (expand_abbreviation(parameter), parameter)
            for parameter in self._station.parameters
        ]
        y = self._station.data.index
        if self._parameter in self._station.parameters:
            x = self._station.data[self._parameter]
            self._parameter_dropdown.label = expand_abbreviation(self._parameter)
        else:
            x = [np.nan] * len(y)

        self._source.data = {"x": x, "y": y}

        self._ocean_floor.top = self._station.water_depth
        self._sync_parameter_options()

    def parameter_selected(self, event):
        self._parameter = event.item
        self._source.data["x"] = self._station.data[self._parameter]
        self._parameter_dropdown.label = expand_abbreviation(self._parameter)

    @property
    def layout(self):
        return column(
            self._parameter_dropdown, self._figure, self._parameter_options_checkbox
        )

    @property
    def y_range(self):
        return self._figure.y_range

    def _toggle_parameter_options(self, attr, old, new):
        if new != self._parameter_options.active_buttons:
            self._parameter_options.from_buttons(new)
            self._sync_parameter_options()

    def _sync_parameter_options(self):
        self._lines.visible = self._parameter_options.show_lines
        self._ocean_floor.visible = self._parameter_options.show_bounds and bool(
            self._station
        )
        self._sea_level.visible = self._parameter_options.show_bounds
        self._sky.visible = self._parameter_options.show_bounds

        self._parameter_options_checkbox.active = self._parameter_options.active_buttons


class ParameterOptions(DataModel):
    show_lines = Bool(default=True)
    show_bounds = Bool(default=True)

    def from_buttons(self, button_selection: list[int]):
        show_lines = 0 in button_selection
        show_bounds = 1 in button_selection
        self.show_lines = show_lines
        self.show_bounds = show_bounds

    @property
    def active_buttons(self):
        active = []
        if self.show_lines:
            active.append(0)
        if self.show_bounds:
            active.append(1)
        return active
