import polars as pl
from bokeh.events import MenuItemClick
from bokeh.layouts import column
from bokeh.models import (
    Button,
    ColumnDataSource,
    CrosshairTool,
    Dropdown,
    HoverTool,
    Label,
    LassoSelectTool,
    Row,
    Span,
    WheelZoomTool,
)
from bokeh.plotting import figure
from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS
from ocean_data_qc.fyskem.qc_flags import QcFlags

from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.base_view import BaseView

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
    "PH_TOT": "Spectrofotometric pH",
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


class ScatterSlot(BaseView):
    def __init__(
        self,
        visits_model: VisitsModel,
        manual_qc_model: ManualQcModel,
        x_parameter: str = "",
        y_parameter: str = "",
    ):
        self._visits_model = visits_model
        self._manual_qc_model = manual_qc_model
        self._manual_qc_model.register_listener(
            ManualQcModel.VALUES_SELECTED, self._on_values_selected
        )

        self._width = 475
        self._height = 475
        self._x_parameter = x_parameter
        self._y_parameter = y_parameter
        self._merged_data = None
        self._applying_highlight = False
        self._source = ColumnDataSource(
            data={"x": [], "y": [], "colors": [], "line_colors": []}
        )

        self._initialize_plot()

    def _initialize_plot(self):
        wheel_zoom = WheelZoomTool()
        self._hover = HoverTool()
        select = LassoSelectTool()

        self._crosshair_width = Span(dimension="width", line_dash="dashed", line_width=1)
        self._crosshair_height = Span(
            dimension="height", line_dash="dashed", line_width=1
        )
        crosshair = CrosshairTool(overlay=[self._crosshair_width, self._crosshair_height])

        self._figure_config = {
            "height": self._height,
            "width": self._width,
            "toolbar_location": "below",
            "tools": ["reset", "pan", wheel_zoom, self._hover, crosshair, select],
        }
        self._plot_values_config = {
            "size": 7,
            "alpha": 0.8,
            "name": "values",
            "color": "colors",
            "line_color": "line_colors",
        }

        self._figure = figure(**self._figure_config)
        self._figure.toolbar.active_scroll = wheel_zoom

        # Add values and lines
        # _parameter_values är punkterna i plotten
        self._parameter_values = self._figure.scatter(
            "x", "y", source=self._source, **self._plot_values_config
        )
        self._source.selected.on_change("indices", self._on_value_selected)
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
            width=190,
        )
        self._x_parameter_dropdown.on_click(self._x_parameter_selected)

        # Add y_parameter selector
        self._y_parameter_dropdown = Dropdown(
            label=expand_abbreviation(self._y_parameter) or "y-parameter",
            button_type="default",
            menu=[],
            name="y_parameter",
            width=190,
        )
        self._y_parameter_dropdown.on_click(self._y_parameter_selected)

        self._swap_axis_button = Button(label="X ↔ Y", width=65)
        self._swap_axis_button.on_click(self._swap_axis_callback)

    def _x_parameter_selected(self, event: MenuItemClick):
        self._x_parameter = event.item
        self._x_parameter_dropdown.label = expand_abbreviation(self._x_parameter)
        self._load_parameters()

    def _y_parameter_selected(self, event: MenuItemClick):
        self._y_parameter = event.item
        self._y_parameter_dropdown.label = expand_abbreviation(self._y_parameter)
        self._load_parameters()

    def _swap_axis_callback(self, event):
        self._x_parameter, self._y_parameter = self._y_parameter, self._x_parameter
        self._x_parameter_dropdown.label = expand_abbreviation(self._x_parameter)
        self._y_parameter_dropdown.label = expand_abbreviation(self._y_parameter)
        self._load_parameters()

    def _load_parameters(self):
        if {self._x_parameter, self._y_parameter} <= set(
            self._visits_model.selected_visit.parameters
        ):
            x_data = self._visits_model.selected_visit.data.filter(
                pl.col("parameter") == self._x_parameter
            ).sort("DEPH")

            y_data = self._visits_model.selected_visit.data.filter(
                pl.col("parameter") == self._y_parameter
            ).sort("DEPH")

            merged_data = x_data.join(y_data, on="DEPH", suffix="_y")

            merged_data = merged_data.with_columns(
                quality_flag_x=[
                    flags.total.value
                    for flags in map(
                        QcFlags.from_string, list(merged_data["quality_flag_long"])
                    )
                ],
                quality_flag_y=[
                    flags.total.value
                    for flags in map(
                        QcFlags.from_string, list(merged_data["quality_flag_long_y"])
                    )
                ],
            )

            qc_flags_x = list(
                map(QcFlags.from_string, list(merged_data["quality_flag_long"]))
            )

            qc_flags_y = list(
                map(QcFlags.from_string, list(merged_data["quality_flag_long_y"]))
            )

            colors = [QC_FLAG_CSS_COLORS.get(flags.total) for flags in qc_flags_x]

            # Evaluate and store all .value values first
            total_values = [flags.total.value for flags in qc_flags_x]
            incoming_values = [flags.incoming.value for flags in qc_flags_x]
            line_colors = [
                "black" if inc != tot else "none"
                for inc, tot in zip(incoming_values, total_values)
            ]

            self._merged_data = merged_data
            self._source.data = {
                "x": list(merged_data["value"]),
                "y": list(merged_data["value_y"]),
                "colors": colors,
                "line_colors": line_colors,
                "deph": list(merged_data["DEPH"]),
                "qcx": [f"{flags.total} ({flags.total.value})" for flags in qc_flags_x],
                "qcy": [f"{flags.total} ({flags.total.value})" for flags in qc_flags_y],
            }

            self._hover.tooltips = [
                (self._x_parameter, "@x"),
                (self._y_parameter, "@y"),
                ("Depth", "@deph"),
                (f"QC {self._x_parameter}", "@qcx"),
                (f"QC {self._y_parameter}", "@qcy"),
            ]
            self._no_data_label.visible = False
        else:
            self._merged_data = None
            self._source.data = {"x": [], "y": [], "colors": [], "line_colors": []}
            self._no_data_label.visible = True

    def update_colors(self, updated_values: list[Parameter]):
        if self._merged_data is None:
            return
        updated_map = {
            (v._data["parameter"], v._data["DEPH"]): QC_FLAG_CSS_COLORS.get(v.qc.total)
            for v in updated_values
        }
        patches = [
            (i, updated_map[(self._x_parameter, row["DEPH"])])
            for i, row in enumerate(self._merged_data.iter_rows(named=True))
            if (self._x_parameter, row["DEPH"]) in updated_map
        ]
        if patches:
            self._source.patch({"colors": patches})

    def _on_value_selected(self, _attr, _old, new):
        if self._applying_highlight or self._merged_data is None:
            return
        parameters = []
        for i in new:
            row = self._merged_data.row(i, named=True)
            parameters.append(
                Parameter(
                    {
                        **row,
                        "parameter": self._x_parameter,
                        "value": row["value"],
                        "quality_flag_long": row["quality_flag_long"],
                    }
                )
            )
            parameters.append(
                Parameter(
                    {
                        **row,
                        "parameter": self._y_parameter,
                        "value": row["value_y"],
                        "quality_flag_long": row["quality_flag_long_y"],
                    }
                )
            )
        self._manual_qc_model.set_values_from_filter(parameters)

    def _on_values_selected(self):
        self._applying_highlight = True
        if self._merged_data is None:
            self._source.selected.indices = []
        else:
            selected_set = {
                (value._data["parameter"], value._data["DEPH"])
                for value in self._manual_qc_model.selected_values
            }
            self._source.selected.indices = [
                i
                for i, row in enumerate(self._merged_data.iter_rows(named=True))
                if (self._x_parameter, row["DEPH"]) in selected_set
                or (self._y_parameter, row["DEPH"]) in selected_set
            ]
        self._applying_highlight = False

    def update_station(self):
        self._x_parameter_dropdown.menu = [
            (expand_abbreviation(parameter), parameter)
            for parameter in self._visits_model.selected_visit.parameters
        ]
        self._y_parameter_dropdown.menu = [
            (expand_abbreviation(parameter), parameter)
            for parameter in self._visits_model.selected_visit.parameters
        ]
        self._load_parameters()

    @property
    def layout(self):
        return column(
            Row(
                children=[
                    self._x_parameter_dropdown,
                    self._swap_axis_button,
                    self._y_parameter_dropdown,
                ]
            ),
            self._figure,
        )
