from typing import Self

from bokeh.colors import RGB
from bokeh.core.enums import Align
from bokeh.core.property.primitive import Bool
from bokeh.events import MenuItemClick
from bokeh.layouts import column
from bokeh.model import DataModel
from bokeh.models import (
    BoxAnnotation,
    CheckboxButtonGroup,
    ColumnDataSource,
    CrosshairTool,
    Dropdown,
    HoverTool,
    Label,
    PolySelectTool,
    Span,
    WheelZoomTool,
)
from bokeh.plotting import figure
from fyskemqc.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from fyskemqc.qc_flags import QcFlags

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


class ParameterSlot(Layoutable):
    def __init__(
        self,
        parameter: str = None,
        linked_parameter: Self = None,
    ):
        self._width = 500
        self._height = 500
        self._parameter = parameter
        self._station = None
        self._source = ColumnDataSource(
            data={
                "x": [],
                "y": [],
                "color": [],
                "QC": [],
                "qc_incoming": [],
                "qc_automatic": [],
                "qc_manual": [],
            }
        )
        self._parameter_options = ParameterOptions()

        self._initialize_plot(linked_parameter)

        # Add buttons for parameter options
        self._parameter_options_checkbox = CheckboxButtonGroup(
            labels=["Lines", "Bounds"], align=Align.center
        )
        self._parameter_options_checkbox.on_change(
            "active", self._toggle_parameter_options
        )
        self._sync_parameter_options()

    def _initialize_plot(self, linked_parameter):
        wheel_zoom = WheelZoomTool()
        hover = HoverTool()
        select = PolySelectTool()
        if linked_parameter:
            self._crosshair_width = linked_parameter._crosshair_width
            self._crosshair_height = linked_parameter._crosshair_height
        else:
            self._crosshair_width = Span(
                dimension="width", line_dash="dashed", line_width=1
            )
            self._crosshair_height = Span(
                dimension="height", line_dash="dashed", line_width=1
            )
        crosshair = CrosshairTool(overlay=[self._crosshair_width, self._crosshair_height])
        self._figure_config = {
            "height": self._height,
            "width": self._width,
            "toolbar_location": "below",
            "tools": ["reset", "pan", wheel_zoom, hover, crosshair, select],
            "tooltips": [
                ("Value", "$x"),
                ("Depth", "$y"),
                ("QC", "@qc"),
                ("Incoming QC", "@qc_incoming"),
                ("Automatic QC", "@qc_automatic"),
                ("Manual QC", "@qc_manual"),
            ],
        }
        self._plot_values_config = {
            "size": 7,
            "alpha": 0.8,
            "name": "values",
        }
        self._plot_line_config = {
            "line_width": 1,
            "color": "navy",
            "alpha": 0.8,
            "name": "connecting_line",
        }
        self._figure = figure(**self._figure_config)
        self._figure.toolbar.active_scroll = wheel_zoom

        # Add sea level and sky
        self._sky = self._figure.image_url(
            url=["qc_tool/static/images/gull.png"], x=0, y=-500
        )
        self._sea_level = BoxAnnotation(
            bottom=0, fill_color="lightskyblue", fill_alpha=0.10
        )
        self._sea_level.level = "underlay"
        self._figure.add_layout(self._sea_level)

        # Add ocean floor
        self._ocean_floor = BoxAnnotation(fill_color=RGB(60, 25, 0), fill_alpha=0.50)
        self._ocean_floor.level = "underlay"
        self._figure.add_layout(self._ocean_floor)

        # Add values and lines
        self._lines = self._figure.line(
            "x", "y", source=self._source, **self._plot_line_config
        )

        self._parameter_values = self._figure.scatter(
            "x", "y", source=self._source, color="color", **self._plot_values_config
        )
        hover.renderers = [self._parameter_values]

        if linked_parameter:
            self._figure.y_range = linked_parameter.y_range
        else:
            self._figure.y_range.flipped = True

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

        # Add parameter selector
        self._parameter_dropdown = Dropdown(
            label=expand_abbreviation(self._parameter) or "Parameter",
            button_type="default",
            menu=[],
            name="parameter",
            width=200,
        )
        self._parameter_dropdown.on_click(self._parameter_selected)

    def update_station(self, station: Station):
        self._station = station
        self._parameter_dropdown.menu = [
            (expand_abbreviation(parameter), parameter)
            for parameter in self._station.parameters
        ]
        self._source.data = {
            "x": [],
            "y": [],
            "color": [],
            "qc": [],
            "qc_incoming": [],
            "qc_automatic": [],
            "qc_manual": [],
        }

        if self._parameter in self._station.parameters:
            self._load_parameter()
            self._no_data_label.visible = False
        else:
            self._no_data_label.visible = True

        self._ocean_floor.top = self._station.water_depth
        self._sync_parameter_options()

    def _parameter_selected(self, event: MenuItemClick):
        self._parameter = event.item
        self._load_parameter()

    def _load_parameter(self):
        parameter_data = self._station.data[
            self._station.data["parameter"] == self._parameter
        ].sort_values("DEPH")

        if "quality_flag_long" not in parameter_data:
            try:
                parameter_data["quality_flag_long"] = parameter_data["quality_flag"].map(
                    lambda x: str(QcFlags(QcFlag.parse(x), None, None))
                )
            except Exception:
                print(self._parameter)
                raise

        parameter_data["QC"] = [
            flags.total
            for flags in map(QcFlags.from_string, parameter_data["quality_flag_long"])
        ]

        qc_flags = list(map(QcFlags.from_string, parameter_data["quality_flag_long"]))

        colors = parameter_data["QC"].map(lambda flag: QC_FLAG_CSS_COLORS[flag])

        self._source.data = {
            "x": parameter_data["value"],
            "y": parameter_data["DEPH"],
            "color": colors,
            "qc": [f"{flags.total} ({flags.total.value})" for flags in qc_flags],
            "qc_incoming": [
                f"{flags.incoming} ({flags.incoming.value})" for flags in qc_flags
            ],
            "qc_automatic": [str(flags.automatic) for flags in qc_flags],
            "qc_manual": [f"{flags.manual} ({flags.manual.value})" for flags in qc_flags],
        }
        self._parameter_dropdown.label = expand_abbreviation(self._parameter)

    @property
    def layout(self):
        return column(
            self._parameter_dropdown,
            self._figure,
            self._parameter_options_checkbox,
        )

    @property
    def y_range(self):
        return self._figure.y_range

    def _toggle_parameter_options(self, attr, old, new):
        if new != self._parameter_options.active_buttons:
            self._parameter_options.from_buttons(new)
            self._sync_parameter_options()

    def _sync_parameter_options(self):
        # Setting visibility of elements according to parameter options
        self._lines.visible = self._parameter_options.show_lines
        self._ocean_floor.visible = self._parameter_options.show_bounds and bool(
            self._station
        )
        self._sea_level.visible = self._parameter_options.show_bounds
        self._sky.visible = self._parameter_options.show_bounds

        # Setting button states according to parameter options
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
