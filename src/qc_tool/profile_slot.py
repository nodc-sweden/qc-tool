from dataclasses import dataclass
from functools import partial
from typing import Self

import pandas as pd
import polars as pl
from bokeh.core import enums
from bokeh.layouts import column
from bokeh.models import (
    BoxAnnotation,
    Button,
    ColumnDataSource,
    CrosshairTool,
    CustomJS,
    HoverTool,
    Label,
    LassoSelectTool,
    LinearAxis,
    Range1d,
    SaveTool,
    Span,
    WheelZoomTool,
)
from bokeh.plotting import figure
from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS

from qc_tool.models.manual_qc_model import ManualQcModel
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


class ProfileData:
    def __init__(self):
        self.title = ""
        self.water_depth = 250


@dataclass(frozen=True)
class SlotConfig:
    parameters: tuple[str, ...]


class ProfileSlot(BaseView):
    _width = 300
    _height = 400

    source_fields = (
        "x",
        "unit",
        "y",
        "color",
        "line_color",
        "qc",
        "qc_incoming",
        "qc_automatic",
        "qc_manual",
    )
    statistics_source_fields = (
        "depth",
        "median",
        "lower_limit",
        "upper_limit",
        "flag2_lower",
        "flag2_upper",
        "flag3_lower",
        "flag3_upper",
        "min",
        "max",
    )

    def __init__(
        self,
        manual_qc_model: ManualQcModel,
        title: str = "",
        linked_plot: Self | None = None,
    ):
        self._title = title
        self._manual_qc_model = manual_qc_model
        self._manual_qc_model.register_listener(
            ManualQcModel.VALUES_SELECTED, self._on_values_selected
        )

        self._parameter_data = []
        self._parameters = ()
        self._configuration = SlotConfig(parameters=())
        self._show_lines = True
        self._show_bounds = True
        self._has_data = False
        self._clear_called = False
        self._applying_highlight = False

        self._point_sources = [
            ColumnDataSource(data={key: [] for key in self.source_fields}),
            ColumnDataSource(data={key: [] for key in self.source_fields}),
            ColumnDataSource(data={key: [] for key in self.source_fields}),
            ColumnDataSource(data={key: [] for key in self.source_fields}),
        ]

        self._line_sources = [
            ColumnDataSource(data={key: [] for key in self.source_fields}),
            ColumnDataSource(data={key: [] for key in self.source_fields}),
            ColumnDataSource(data={key: [] for key in self.source_fields}),
            ColumnDataSource(data={key: [] for key in self.source_fields}),
        ]

        self._statistics_source = ColumnDataSource(
            data={key: [] for key in self.statistics_source_fields}
        )

        wheel_zoom = WheelZoomTool()
        hover = HoverTool()
        select = LassoSelectTool()
        save = SaveTool()

        if linked_plot:
            self._crosshair_line = linked_plot._crosshair_line
        else:
            self._crosshair_line = Span(line_dash="dashed", line_width=1)
        crosshair = CrosshairTool(overlay=self._crosshair_line)

        self._figure_config = {
            "title": self._title,
            "height": self._height,
            "width": self._width,
            "toolbar_location": "below",
            "tools": ["pan", wheel_zoom, hover, crosshair, select, save],
            "output_backend": "webgl",
            "tooltips": [
                ("Parameter", "$name"),
                ("Value", "@x"),
                ("Unit", "@unit"),
                ("Depth", "@y"),
                ("QC", "@qc"),
                ("Incoming QC", "@qc_incoming"),
                ("Automatic QC", "@qc_automatic"),
                ("Manual QC", "@qc_manual"),
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
        self._figure.xaxis.visible = False
        # add xaxis to possible parameters
        self._extra_axes = []
        max_number_of_parameters = len(self._point_sources)
        for i in range(max_number_of_parameters):
            range_name = f"x{i + 1}"
            self._figure.extra_x_ranges[range_name] = Range1d(start=0, end=1)
            extra_axis = LinearAxis(x_range_name=range_name, visible=False)
            self._figure.add_layout(extra_axis, "above")
            self._extra_axes.append(extra_axis)
        # set axes ranges
        self._axes_range_sources = [
            ColumnDataSource(
                data={
                    "range_name": [],
                    "x_min": [],
                    "x_max": [],
                    "y_min": [],
                    "y_max": [],
                }
            )
            for _ in range(max_number_of_parameters)
        ]
        self._init_background()
        self._init_statistics_plot()

        # Add values and lines
        self._lines = [
            self._figure.line(
                "x", "y", source=source, line_dash=dash, **self._plot_line_config
            )
            for source, dash in zip(self._line_sources, enums.DashPattern)
        ]
        self._values = [
            self._figure.scatter(
                "x",
                "y",
                source=source,
                color="color",
                line_color="line_color",
                **self._plot_values_config,
            )
            for source in self._point_sources
        ]

        self._point_sources[0].selected.on_change(
            "indices", partial(self._on_value_selected, index=0)
        )
        self._point_sources[1].selected.on_change(
            "indices", partial(self._on_value_selected, index=1)
        )
        self._point_sources[2].selected.on_change(
            "indices", partial(self._on_value_selected, index=2)
        )
        self._point_sources[3].selected.on_change(
            "indices", partial(self._on_value_selected, index=3)
        )

        hover.renderers = self._values

        if linked_plot:
            self._figure.y_range = linked_plot.y_range
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

        # add dynamic reset button to all axes
        self._reset_button = Button(label="Reset", width=80)
        self._reset_button.js_on_click(
            CustomJS(
                args=dict(
                    figure=self._figure,
                    axes_ranges=self._axes_range_sources,
                ),
                code="""
                    for (let i = 0; i < axes_ranges.length; i++) {
                        let src = axes_ranges[i];
                        if (!src.data['range_name'].length) continue;

                        let name = src.data['range_name'][0];
                        figure.extra_x_ranges[name].start = src.data['x_min'][0];
                        figure.extra_x_ranges[name].end   = src.data['x_max'][0];

                        figure.y_range.end = src.data['y_min'][0];
                        figure.y_range.start = src.data['y_max'][0];
                    }
                    """,
            )
        )

    def _init_background(self):
        # Add sea level and sky
        self._sea_level = BoxAnnotation(
            bottom=0, fill_color="lightskyblue", fill_alpha=0.10
        )
        self._sea_level.level = "underlay"
        self._figure.add_layout(self._sea_level)

        # Add ocean floor
        self._ocean_floor = Span(
            location=0, dimension="width", line_width=2, line_color="brown"
        )
        self._figure.add_layout(self._ocean_floor)

    def _init_statistics_plot(self):
        self._plot_line_statistics_config = {
            "line_width": 4,
            "color": "black",
            "alpha": 0.3,
        }
        self._plot_dash_statistics_config = {
            "line_width": 2,
            "size": 10,
            "color": "black",
            "alpha": 0.3,
        }
        self._plot_area_statistics_config = {
            "color": "grey",
            "alpha": 0.1,
        }
        self._plot_flag3_fill_statistics_config = {
            "color": "orange",
            "alpha": 0.1,
        }
        self._plot_line_min_max_config = {"color": "red", "line_width": 0.5, "alpha": 0.5}

        # Add statistics
        self._median_values_line = self._figure.line(
            "median",
            "depth",
            source=self._statistics_source,
            **self._plot_line_statistics_config,
        )
        self._median_values_dash = self._figure.scatter(
            "median",
            "depth",
            marker="dash",
            source=self._statistics_source,
            **self._plot_dash_statistics_config,
        )
        self._limits_area = self._figure.harea(
            x1="lower_limit",
            x2="upper_limit",
            y="depth",
            source=self._statistics_source,
            **self._plot_area_statistics_config,
        )
        self._flag3_lower_limits_area = self._figure.harea(
            x1="flag3_lower",
            x2="flag2_lower",
            y="depth",
            source=self._statistics_source,
            **self._plot_flag3_fill_statistics_config,
        )
        self._flag3_upper_limits_area = self._figure.harea(
            x1="flag3_upper",
            x2="flag2_upper",
            y="depth",
            source=self._statistics_source,
            **self._plot_flag3_fill_statistics_config,
        )
        self._min_line = self._figure.line(
            "min",
            "depth",
            source=self._statistics_source,
            **self._plot_line_min_max_config,
        )
        self._max_line = self._figure.line(
            "max",
            "depth",
            source=self._statistics_source,
            **self._plot_line_min_max_config,
        )

    def set_data(
        self,
        title: str = "",
        data: list[tuple[str, dict | None, pl.DataFrame | None]] | None = None,
        max_depth: float | None = None,
        water_depth: float | None = None,
    ):

        self._parameter_data = []
        data = data or []
        self._figure.title.text = expand_abbreviation(title)
        # get data, units, and ranges
        unit_to_range = {}
        axis_index = 0
        self._parameters = tuple(parameter_name for parameter_name, _, _ in data)
        for i, (
            (parameter_name, parameter_data, parameter_ctd_data),
            point_source,
            line_source,
            values,
        ) in enumerate(zip(data, self._point_sources, self._line_sources, self._values)):
            # if data is missing make sure plot gets empty data to not show old data
            if parameter_data is None:
                point_source.data = {key: [] for key in self.source_fields}
                line_source.data = {key: [] for key in self.source_fields}
                self._parameter_data.append(None)
                continue
            # update points and lines with the new data
            point_source.data = parameter_data
            if parameter_ctd_data is not None and len(parameter_ctd_data):
                line_source.data = {
                    "x": list(parameter_ctd_data[parameter_name.replace("BTL", "CTD")]),
                    "y": list(parameter_ctd_data["DEPTH_CTD"]),
                }
            else:
                line_source.data = parameter_data

            values.name = expand_abbreviation(parameter_name)
            self._parameter_data.append(parameter_data["data"])

            unit = parameter_data["unit"][0] if parameter_data["unit"] else ""
            x_values = [v for v in parameter_data["x"] if v is not None]
            line_x_values = [v for v in line_source.data["x"] if v is not None]
            x_values = set(x_values) | set(line_x_values)

            if not x_values:
                continue

            axis_index = self._sync_axes(
                unit,
                parameter_name,
                x_values,
                i,
                unit_to_range,
                axis_index,
                water_depth,
                max_depth,
            )
        self._sync_profile_options(water_depth, max_depth)

    def _sync_profile_options(self, water_depth=None, max_depth=None):

        self._has_data = any(source.data.get("x") for source in self._point_sources)

        for lines in self._lines:
            lines.visible = self._show_lines
        self._ocean_floor.visible = self._show_bounds and self.has_data
        self._no_data_label.visible = not self.has_data
        self._sea_level.visible = self._show_bounds and self.has_data
        self._ocean_floor.location = max(
            d for d in [water_depth, max_depth, 0] if d is not None
        )

    def _sync_axes(
        self,
        unit,
        parameter_name,
        x_values,
        renderer_index,
        unit_to_range,
        axis_index,
        water_depth=None,
        max_depth=None,
    ):
        # set yaxis range
        y_min = -5
        y_max = max(d for d in [water_depth, max_depth, 0] if d is not None) + 5
        self._figure.y_range.start = y_max
        self._figure.y_range.end = y_min

        # get xaxis range
        x_min = min(x_values)
        x_max = max(x_values)
        padding = 0.1 * (x_max - x_min)
        min_padding = padding
        if padding == 0:
            # single point and identical values
            padding = abs(x_min) * 0.1 if x_min != 0 else 1
        if 0 < x_min <= 0.2:
            x_min_padded = -0.05
            min_padding = 0.1
        else:
            x_min_padded = x_min - padding

        x_max_padded = x_max + padding

        if unit in unit_to_range:
            range_name = unit_to_range[unit]
            rng = self._figure.extra_x_ranges[range_name]
            # set xaxis range
            rng.start = min(rng.start - min_padding, x_min_padded)
            rng.end = max(rng.end + padding, x_max_padded)
            # add info to reset button
            for src in self._axes_range_sources:
                if src.data["range_name"] and src.data["range_name"][0] == range_name:
                    src.data = {
                        "range_name": [range_name],
                        "x_min": [rng.start],
                        "x_max": [rng.end],
                        "y_min": [y_min],
                        "y_max": [y_max],
                    }
                    break
        else:
            axis_index += 1
            range_name = f"x{axis_index}"
            rng = self._figure.extra_x_ranges[range_name]
            # set xaxis range
            rng.start = x_min_padded
            rng.end = x_max_padded
            # set unit to axis
            axis_label = unit if unit else expand_abbreviation(parameter_name)
            self._extra_axes[axis_index - 1].axis_label = axis_label
            self._extra_axes[axis_index - 1].visible = True
            unit_to_range[unit] = range_name
            # add info to reset button
            self._axes_range_sources[axis_index - 1].data = {
                "range_name": [range_name],
                "x_min": [x_min_padded],
                "x_max": [x_max_padded],
                "y_min": [y_min],
                "y_max": [y_max],
            }

        self._values[renderer_index].x_range_name = range_name
        self._lines[renderer_index].x_range_name = range_name

        # plot statistics against the same xaxis
        if renderer_index == 0:
            self._median_values_line.x_range_name = range_name
            self._median_values_dash.x_range_name = range_name
            self._limits_area.x_range_name = range_name
            self._flag3_lower_limits_area.x_range_name = range_name
            self._flag3_upper_limits_area.x_range_name = range_name
            self._min_line.x_range_name = range_name
            self._max_line.x_range_name = range_name

        return axis_index

    def select_values(self, index, rows):
        selected_values = [
            Parameter(self._parameter_data[index].row(n, named=True)) for n in rows
        ]
        self._statistics_source.selected.indices = []
        if not self._clear_called:
            self._manual_qc_model.set_selected_values(selected_values)

    def update_colors(self, updated_values: list[Parameter]):
        updated_map = {
            (
                value._data["visit_key"],
                value._data["parameter"],
                value._data["DEPH"],
            ): value
            for value in updated_values
        }

        for source, parameter_data in zip(self._point_sources, self._parameter_data):
            if parameter_data is None:
                continue

            color_patches = []
            qc_patches = []
            qc_incoming_patches = []
            qc_automatic_patches = []
            qc_manual_patches = []

            for i, row in enumerate(parameter_data.iter_rows(named=True)):
                key = (row["visit_key"], row["parameter"], row["DEPH"])

                if key not in updated_map:
                    continue

                value = updated_map[key]
                flags = value.qc

                qc_str = f"{flags.total} ({flags.total.value})"
                qc_incoming_str = f"{flags.incoming} ({flags.incoming.value})"
                qc_automatic_str = f"{flags.total_automatic} {flags.total_automatic_name}"
                qc_manual_str = f"{flags.manual} ({flags.manual.value})"

                color = QC_FLAG_CSS_COLORS.get(flags.total)

                color_patches.append((i, color))
                qc_patches.append((i, qc_str))
                qc_incoming_patches.append((i, qc_incoming_str))
                qc_automatic_patches.append((i, qc_automatic_str))
                qc_manual_patches.append((i, qc_manual_str))

            if color_patches:
                saved_indices = list(source.selected.indices)
                self._applying_highlight = True

                source.patch(
                    {
                        "color": color_patches,
                        "qc": qc_patches,
                        "qc_incoming": qc_incoming_patches,
                        "qc_automatic": qc_automatic_patches,
                        "qc_manual": qc_manual_patches,
                    }
                )

                if saved_indices:
                    source.selected.indices = saved_indices

                self._applying_highlight = False

    def _on_values_selected(self):
        self._applying_highlight = True
        for index, (source, parameter_data) in enumerate(
            zip(self._point_sources, self._parameter_data)
        ):
            if parameter_data is None:
                source.selected.indices = []
                continue
            selected = self._manual_qc_model.selected_values
            indices = [
                i
                for i, row in enumerate(parameter_data.iter_rows(named=True))
                if any(
                    row["visit_key"] == value._data["visit_key"]
                    and row["parameter"] == value._data["parameter"]
                    and row["DEPH"] == value._data["DEPH"]
                    for value in selected
                )
            ]
            source.selected.indices = indices
        self._applying_highlight = False

    def _on_value_selected(self, attr, old, new, index):
        if not self._applying_highlight:
            self.select_values(index, new)

    def update_statistics(self, parameter_statistics, water_depth):
        if parameter_statistics is None:
            self._statistics_source.data = {
                key: [] for key in self.statistics_source_fields
            }
            return

        statistics = pd.DataFrame(parameter_statistics)
        filtered_stats = statistics[statistics["depth"] <= water_depth * 1.1]

        # Update the Bokeh data source with the filtered statistics
        self._statistics_source.data = {
            "depth": filtered_stats["depth"].tolist(),
            "median": filtered_stats["median"].tolist(),
            "lower_limit": filtered_stats["25p"].tolist(),
            "upper_limit": filtered_stats["75p"].tolist(),
            "min": filtered_stats["min"].tolist(),
            "max": filtered_stats["max"].tolist(),
            "flag2_lower": filtered_stats["flag2_lower"].tolist(),
            "flag2_upper": filtered_stats["flag2_upper"].tolist(),
            "flag3_lower": filtered_stats["flag3_lower"].tolist(),
            "flag3_upper": filtered_stats["flag3_upper"].tolist(),
        }

    def configure(self, configuration: SlotConfig):
        # if configuration == self._configuration:
        #             return False
        self._configuration = configuration
        # configuration-related Bokeh work here
        # return True

    @property
    def configuration(self) -> SlotConfig:
        return self._configuration

    @property
    def has_data(self) -> bool:
        return self._has_data

    @property
    def layout(self):
        return column(self._figure, self._reset_button)

    @property
    def y_range(self):
        return self._figure.y_range
