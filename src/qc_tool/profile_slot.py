from functools import partial
from typing import Self

import pandas as pd
from bokeh.colors import RGB
from bokeh.core import enums
from bokeh.core.property.primitive import Bool
from bokeh.model import DataModel
from bokeh.models import (
    BoxAnnotation,
    ColumnDataSource,
    CrosshairTool,
    HoverTool,
    Label,
    LassoSelectTool,
    SaveTool,
    Span,
    WheelZoomTool,
)
from bokeh.plotting import figure
from ocean_data_qc.fyskem.parameter import Parameter

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
        self.water_depth = 50


class ProfileSlot(BaseView):
    _width = 300
    _height = 400

    source_fields = (
        "x",
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

        self._station = None
        self._data = None
        self._parameter_data = []
        self._show_lines = True
        self._show_bounds = True
        self._clear_called = False

        self._sources = [
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
            "tools": ["reset", "pan", wheel_zoom, hover, crosshair, select, save],
            "output_backend": "webgl",
            "tooltips": [
                ("Parameter", "$name"),
                ("Value", "@x"),
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

        self._init_background()
        self._init_statistics_plot()

        # Add values and lines
        self._lines = [
            self._figure.line(
                "x", "y", source=source, line_dash=dash, **self._plot_line_config
            )
            for source, dash in zip(self._sources, enums.DashPattern)
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
            for source in self._sources
        ]

        self._sources[0].selected.on_change(
            "indices", partial(self._on_value_selected, index=0)
        )
        self._sources[1].selected.on_change(
            "indices", partial(self._on_value_selected, index=1)
        )
        self._sources[2].selected.on_change(
            "indices", partial(self._on_value_selected, index=2)
        )
        self._sources[3].selected.on_change(
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

    def _init_background(self):
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
        self._ocean_floor.visible = False
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
        data: list[tuple[str, dict]] | None = None,
        station=None,
    ):
        self.clear_selection()
        self._station = station
        self._parameter_data = []

        for source in self._sources:
            source.data = {key: [] for key in self.source_fields}

        self._statistics_source.data = {key: [] for key in self.statistics_source_fields}

        self._figure.title.text = expand_abbreviation(title)
        for (parameter_name, parameter_data), source, values in zip(
            data, self._sources, self._values
        ):
            if parameter_data is None:
                self._parameter_data.append(None)
                continue
            source.data = parameter_data
            values.name = expand_abbreviation(parameter_name)
            self._parameter_data.append(parameter_data["data"])

        self._sync_profile_options()

    def _sync_profile_options(self):
        # Setting the visibility of elements according to parameter options
        has_data = any(source.data.get("x") for source in self._sources)

        for lines in self._lines:
            lines.visible = self._show_lines
        self._ocean_floor.visible = self._show_bounds and has_data
        self._no_data_label.visible = not has_data
        self._sea_level.visible = self._show_bounds and has_data
        self._sky.visible = self._show_bounds and has_data
        if self._station is not None:
            self._ocean_floor.top = self._station.water_depth

    def clear_selection(self):
        self._clear_called = True
        for source in self._sources:
            source.selected.indices = []
        self._clear_called = False

    def select_values(self, index, rows):
        selected_values = [
            (n, Parameter(self._parameter_data[index].row(n, named=True))) for n in rows
        ]
        self._statistics_source.selected.indices = []
        if not self._clear_called:
            self._manual_qc_model.set_selected_values(index, selected_values, self)

    def _on_value_selected(self, attr, old, new, index):
        self.select_values(index, new)

    def update_statistics(self, parameter_statistics, water_depth):
        if parameter_statistics is None:
            self._statistics_source.data = {
                key: [] for key in self.statistics_source_fields
            }
            return

        # Convert the statistical data to a DataFrame for easier filtering
        stats_df = pd.DataFrame(parameter_statistics)

        # Filter rows where 'depth' is less than or equal to self._station.water_depth
        filtered_stats = stats_df[stats_df["depth"] <= water_depth * 1.1]

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

    @property
    def layout(self):
        return self._figure

    @property
    def y_range(self):
        return self._figure.y_range


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
