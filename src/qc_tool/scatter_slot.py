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
    SaveTool,
    Span,
    WheelZoomTool,
)
from bokeh.plotting import figure
from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS

from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.models.scatter_model import ScatterModel
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


class AllScattersData:
    def __init__(self):
        self.title = ""


class ScatterSlot(BaseView):
    _width = 475
    _height = 475

    source_fields = (
        "x_name",
        "x",
        "x_unit",
        "y_name",
        "y",
        "y_unit",
        "depth",
        "color",
        "line_color",
        "qcx",
        "qcy",
    )
    filtered_source_fields = (
        "x",
        "y",
    )

    def __init__(
        self,
        manual_qc_model: ManualQcModel,
        scatter_model: ScatterModel,
        title: str = "",
        x_parameter: str = "",
        y_parameter: str = "",
        scatter_index: int | None = None,
    ):
        self._title = title
        self._manual_qc_model = manual_qc_model
        self._scatter_model = scatter_model
        self._x_parameter = x_parameter
        self._y_parameter = y_parameter
        self._merged_data = None
        self._scatter_index = scatter_index

        self._manual_qc_model.register_listener(
            ManualQcModel.VALUES_SELECTED, self._on_values_selected
        )

        self._visit = None
        self._filtered_data = None
        self._show_lines = True
        self._show_bounds = True
        self._clear_called = False
        self._applying_highlight = False

        self._source = ColumnDataSource(data={key: [] for key in self.source_fields})
        self._filtered_source = ColumnDataSource(
            data={key: [] for key in self.filtered_source_fields}
        )

        self._x_parameter_dropdown = Dropdown(
            label=expand_abbreviation(self._x_parameter) or "x-parameter",
            button_type="default",
            menu=[],
            width=190,
        )
        self._x_parameter_dropdown.on_click(self._x_parameter_selected)

        self._y_parameter_dropdown = Dropdown(
            label=expand_abbreviation(self._y_parameter) or "y-parameter",
            button_type="default",
            menu=[],
            width=190,
        )
        self._y_parameter_dropdown.on_click(self._y_parameter_selected)

        self._swap_axis_button = Button(label="X ↔ Y", width=65)
        self._swap_axis_button.on_click(self._swap_axis_callback)

        wheel_zoom = WheelZoomTool()
        hover = HoverTool()
        select = LassoSelectTool()
        save = SaveTool()

        self._crosshair_line = Span(line_dash="dashed", line_width=1)
        crosshair = CrosshairTool(overlay=self._crosshair_line)

        self._figure_config = {
            # "title": self._title,
            "height": self._height,
            "width": self._width,
            "toolbar_location": "below",
            "tools": ["pan", "reset", wheel_zoom, hover, crosshair, select, save],
            "output_backend": "webgl",
            "tooltips": [
                ("x-parameter", "@x_name"),
                ("x-value", "@x"),
                ("x-unit", "@x_unit"),
                ("x-qc", "@qcx"),
                ("y-parameter", "@y_name"),
                ("y-value", "@y"),
                ("y-unit", "@y_unit"),
                ("y-qc", "@qcy"),
            ],
        }
        self._plot_values_config = {
            "size": 8,
            "alpha": 0.8,
        }
        self._plot_line_config = {
            "line_width": 1,
            "color": "navy",
            "alpha": 0.8,
        }

        self._figure = figure(**self._figure_config)

        # Add background
        self._filtered_values = self._figure.scatter(
            "x",
            "y",
            source=self._filtered_source,
            size=5,
            alpha=0.5,
            color="gray",
        )

        # Add values and line
        self._line = self._figure.line(
            "x",
            "y",
            source=self._source,
            **self._plot_line_config,
        )
        self._values = self._figure.scatter(
            "x",
            "y",
            source=self._source,
            color="color",
            line_color="line_color",
            **self._plot_values_config,
        )

        self._source.selected.on_change("indices", self._on_value_selected)

        hover.renderers = [self._values]

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

    def _x_parameter_selected(self, event: MenuItemClick):
        if event.item == self._x_parameter:
            return
        self._x_parameter = event.item
        self._x_parameter_dropdown.label = expand_abbreviation(self._x_parameter)
        self._scatter_model.selected_scatter_index = self._scatter_index

    def _y_parameter_selected(self, event: MenuItemClick):
        if event.item == self._y_parameter:
            return
        self._y_parameter = event.item
        self._y_parameter_dropdown.label = expand_abbreviation(self._y_parameter)
        self._scatter_model.selected_scatter_index = self._scatter_index

    def _swap_axis_callback(self, event):
        self._x_parameter, self._y_parameter = self._y_parameter, self._x_parameter
        self._x_parameter_dropdown.label = expand_abbreviation(self._x_parameter)
        self._y_parameter_dropdown.label = expand_abbreviation(self._y_parameter)
        self._scatter_model.selected_scatter_index = self._scatter_index

    def clear_figure(self):
        self.clear_selection()
        self._source.data = {key: [] for key in self.source_fields}
        self._filtered_source.data = {key: [] for key in self.filtered_source_fields}
        self._no_data_label.visible = True

    def set_data(
        self,
        x_parameter: str,
        y_parameter: str,
        source_data: dict | None = None,
        merged_data: pl.DataFrame | None = None,
        visit=None,
    ):
        self._visit = visit

        # clear previous content
        self.clear_figure()

        # get data, units, and ranges
        if merged_data is None:
            return

        self._source.data = source_data
        self._merged_data = merged_data
        self._sync_profile_options()

    def set_filtered_data(
        self,
        filtered_data: dict | None,
    ):
        self._filtered_data = filtered_data

        if filtered_data is None:
            self._filtered_source.data = {key: [] for key in self.filtered_source_fields}
            return

        self._filtered_source.data = {
            "x": filtered_data.get("x", []),
            "y": filtered_data.get("y", []),
        }

    def _sync_profile_options(self):
        has_data = any(self._source.data.get("x"))

        self._line.visible = self._show_lines
        self._no_data_label.visible = not has_data

    def clear_selection(self):
        self._clear_called = True
        self._source.selected.indices = []
        self._clear_called = False

    def update_colors(self, updated_values: list[Parameter]):
        if self._merged_data is None:
            return

        updated_map_x = {
            (v._data["parameter"], v._data["DEPH"]): v
            for v in updated_values
            if v._data["parameter"] == self._x_parameter
        }
        updated_map_y = {
            (v._data["parameter"], v._data["DEPH"]): v
            for v in updated_values
            if v._data["parameter"] == self._y_parameter
        }

        if not updated_map_x and not updated_map_y:
            return

        color_patches = []
        qcx_patches = []
        qcy_patches = []

        for i, row in enumerate(self._merged_data.iter_rows(named=True)):
            key_x = (self._x_parameter, row["DEPH"])
            key_y = (self._y_parameter, row["DEPH"])

            if key_x in updated_map_x:
                value_x = updated_map_x[key_x]
                flags_x = value_x.qc
                color = QC_FLAG_CSS_COLORS.get(flags_x.total)
                qc_str_x = f"{flags_x.total} ({flags_x.total.value})"
                color_patches.append((i, color))
                qcx_patches.append((i, qc_str_x))
            if key_y in updated_map_y:
                value_y = updated_map_y[key_y]
                flags_y = value_y.qc
                qc_str_y = f"{flags_y.total} ({flags_y.total.value})"
                qcy_patches.append((i, qc_str_y))

        if color_patches or qcx_patches or qcy_patches:
            saved_indices = list(self._source.selected.indices)
            self._applying_highlight = True

            patch_dict = {}
            if color_patches:
                patch_dict["color"] = color_patches
            if qcx_patches:
                patch_dict["qcx"] = qcx_patches
            if qcy_patches:
                patch_dict["qcy"] = qcy_patches

            self._source.patch(patch_dict)

            if saved_indices:
                self._source.selected.indices = saved_indices

            self._applying_highlight = False

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

    def select_values(self, rows):
        selected_values = [
            Parameter(self._parameter_data.row(n, named=True)) for n in rows
        ]
        if not self._clear_called:
            self._manual_qc_model.set_selected_values(selected_values)

    def _on_value_selected(self, attr, old, new):
        if not self._applying_highlight:
            self.select_values(new)

    @property
    def x_parameter(self) -> str:
        return self._x_parameter

    @property
    def y_parameter(self) -> str:
        return self._y_parameter

    @property
    def scatter_index(self) -> int | None:
        return self._scatter_index

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
