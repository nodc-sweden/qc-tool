import pandas as pd
from bokeh.events import MenuItemClick
from bokeh.layouts import column
from bokeh.models import (
    ColumnDataSource,
    CrosshairTool,
    Dropdown,
    HoverTool,
    Label,
    Span,
    WheelZoomTool,
)
from bokeh.plotting import figure

from qc_tool.protocols import Layoutable
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


class ScatterSlot(Layoutable):
    def __init__(
        self,
        x_parameter: str = "",
        y_parameter: str = "",
    ):
        self._width = 500
        self._height = 500
        self._x_parameter = x_parameter
        self._y_parameter = y_parameter
        self._station = None
        self._source = ColumnDataSource(data={"x": [], "y": []})

        self._initialize_map()

    def _initialize_map(self):
        wheel_zoom = WheelZoomTool()
        self._hover = HoverTool()

        self._crosshair_width = Span(dimension="width", line_dash="dashed", line_width=1)
        self._crosshair_height = Span(
            dimension="height", line_dash="dashed", line_width=1
        )
        crosshair = CrosshairTool(overlay=[self._crosshair_width, self._crosshair_height])

        self._figure_config = {
            "height": self._height,
            "width": self._width,
            "toolbar_location": "below",
            "tools": ["reset", "pan", wheel_zoom, self._hover, crosshair],
        }
        self._plot_values_config = {
            "size": 7,
            "color": "navy",
            "alpha": 0.8,
            "name": "values",
        }

        self._figure = figure(**self._figure_config)
        self._figure.toolbar.active_scroll = wheel_zoom

        # Add values and lines
        # _parameter_values är punkterna i plotten
        self._parameter_values = self._figure.scatter(
            "x", "y", source=self._source, **self._plot_values_config
        )
        self._hover.renderers = [self._parameter_values]

        # Add label to show when parameter is missing
        self._no_data_label = Label(
            x=self._width // 2,
            y=self._height // 2,
            x_units="screen",
            y_units="screen",
            text="No data",
            text_align="center",
            text_baseline="middle",
            text_font_style="bold",
        )
        self._figure.add_layout(self._no_data_label)

        # Add x_parameter selector
        self._x_parameter_dropdown = Dropdown(
            label=expand_abbreviation(self._x_parameter) or "x-parameter",
            button_type="default",
            menu=[],
            name="x_parameter",
            width=200,
        )
        self._x_parameter_dropdown.on_click(self._x_parameter_selected)

        # Add y_parameter selector
        self._y_parameter_dropdown = Dropdown(
            label=expand_abbreviation(self._y_parameter) or "y-parameter",
            button_type="default",
            menu=[],
            name="y_parameter",
            width=200,
        )
        self._y_parameter_dropdown.on_click(self._y_parameter_selected)

    def _x_parameter_selected(self, event: MenuItemClick):
        self._x_parameter = event.item
        self._x_parameter_dropdown.label = expand_abbreviation(self._x_parameter)
        self._load_parameters()

    def _y_parameter_selected(self, event: MenuItemClick):
        self._y_parameter = event.item
        self._y_parameter_dropdown.label = expand_abbreviation(self._y_parameter)
        self._load_parameters()

    def _load_parameters(self):
        if {self._x_parameter, self._y_parameter} <= set(self._station.parameters):
            x_data = self._station.data[
                self._station.data["parameter"] == self._x_parameter
            ].sort_values("DEPH")

            y_data = self._station.data[
                self._station.data["parameter"] == self._y_parameter
            ].sort_values("DEPH")

            merged_data = pd.merge(x_data, y_data, on="DEPH", suffixes=("_x", "_y"))

            self._source.data = {
                "x": merged_data["value_x"],
                "y": merged_data["value_y"],
            }
            self._hover.tooltips = [(self._x_parameter, "@x"), (self._y_parameter, "@y")]
            self._no_data_label.visible = False
        else:
            self._source.data = {"x": [], "y": []}
            self._no_data_label.visible = True

    def update_station(self, station: Station):
        self._station = station
        self._x_parameter_dropdown.menu = [
            (expand_abbreviation(parameter), parameter)
            for parameter in self._station.parameters
        ]
        self._y_parameter_dropdown.menu = [
            (expand_abbreviation(parameter), parameter)
            for parameter in self._station.parameters
        ]
        self._load_parameters()

    @property
    def layout(self):
        return column(
            self._x_parameter_dropdown, self._y_parameter_dropdown, self._figure
        )
