from dataclasses import dataclass
from typing import Optional, Self

import pandas as pd
import polars as pl
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
    LassoSelectTool,
    MultiChoice,
    Span,
    WheelZoomTool,
)
from bokeh.plotting import figure
from ocean_data_qc import statistic
from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flags import QcFlags

from qc_tool.layoutable import Layoutable
from qc_tool.station import Station, get_available_parameters_from_stations

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


@dataclass
class SeriesSpecification:
    parameter: str
    station: Station


class ProfileSlotBase(Layoutable):
    """
    - Initialize the figure and the ColumnDataSources.
    - Provide a method set_series(series_list: list[SeriesSpec]).
    - Handle fetching/transforming/loading in _load_series.
    """

    def __init__(self, value_selected_callback=None, selected_parameters=None):
        self._value_selected_callback = value_selected_callback or (lambda *args: None)
        self._selected_parameters = selected_parameters
        self._series: list[SeriesSpecification] = []
        self._width = 300
        self._height = 400
        self._initialize_plot()
        # Store series info per (station, parameter)
        self._series_glyphs = {}  # key: SeriesSpecification -> dict of glyphs
        self._series_sources = {}  # key: SeriesSpecification -> dict of ColumnDataSource
        self._series_keys = []

        # --- MultiChoice widget for parameter selection ---
        self._parameter_multichoice = MultiChoice(
            title="Select Parameters",
            options=[],  # will be updated in update_stations
            value=[],  # active selection
            height=100,
            width=300,
        )
        self._parameter_multichoice.on_change("value", self._on_parameters_changed)

    def _initialize_plot(self, linked_parameter=None):
        # figure tools
        wheel_zoom = WheelZoomTool()
        hover = HoverTool()
        select = LassoSelectTool()

        #  Crosshairs (share with linked parameter if available)
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
                ("Source", "@series_label"),
                ("Value", "@x"),
                ("Depth", "@y"),
                ("QC", "@qc"),
                ("Incoming QC", "@qc_incoming"),
                ("Automatic QC", "@qc_automatic"),
                ("Manual QC", "@qc_manual"),
            ],
            "y_axis_label": "Depth [m]",
        }
        self._figure = figure(**self._figure_config)
        self._figure.toolbar.active_scroll = wheel_zoom
        # Keep a handle to hover so we can add renderers later
        self._hover_tool = hover
        self._hover_renderers = []

        # Add sea level and sky
        self._sky = self._figure.image_url(
            url=["qc_tool/static/images/gull.png"], x=0, y=-500
        )
        self._sea_level = BoxAnnotation(
            bottom=0, fill_color="lightskyblue", fill_alpha=0.10
        )
        self._sea_level.level = "underlay"
        self._figure.add_layout(self._sea_level)

        # Add ocean floor placeholder (bounds will be set dynamically)
        self._ocean_floor = BoxAnnotation(fill_color=RGB(60, 25, 0), fill_alpha=0.50)
        self._ocean_floor.level = "underlay"
        self._figure.add_layout(self._ocean_floor)

        # Y range setup
        if linked_parameter:
            self._figure.y_range = linked_parameter.y_range
        else:
            self._figure.y_range.flipped = True

        self._plot_values_config = {
            "size": 8,
            "alpha": 0.8,
            "name": "values",
        }
        self._plot_line_config = {
            "line_width": 1,
            "color": "navy",
            "alpha": 0.8,
            "name": "connecting_line",
        }
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
        self._plot_line_min_max_config = {"color": "red", "line_width": 0.5, "alpha": 0.5}

    def _make_data_source(self) -> ColumnDataSource:
        return ColumnDataSource(
            data={
                "x": [],
                "y": [],
                "color": [],
                "line_color": [],
                "qc": [],
                "qc_incoming": [],
                "qc_automatic": [],
                "qc_manual": [],
                "series_label": [],
            }
        )

    def _make_statistics_source(self) -> ColumnDataSource:
        return ColumnDataSource(
            data={
                "depth": [],
                "median": [],
                "lower_limit": [],
                "upper_limit": [],
                "min": [],
                "max": [],
            }
        )

    def set_series(self, series: list[SeriesSpecification]):
        print("set series")
        self._series = series
        self._load_series()

    def _update_series(self):
        self._series.clear()
        for station in self._stations:
            for parameter in self._selected_parameters:
                spec = SeriesSpecification(parameter=parameter, station=station)
                self._series.append(spec)

    # ------------------------------
    # Station + parameter management
    # ------------------------------
    def update_stations(self, stations: list):
        """
        Called from main.py with selected station(s).
        Updates parameter options in multichoice accordingly.
        """
        self._stations = stations or []

        # Get available parameters
        available_params = get_available_parameters_from_stations(self._stations)

        # Update widget options
        self._parameter_multichoice.options = list(
            zip(available_params, map(expand_abbreviation, available_params))
        )

        if self._selected_parameters:
            self._parameter_multichoice.value = self._selected_parameters

        # Default behavior:
        # - If multiple stations: only allow one parameter at a time (preselect first)
        # - If one or no stations keep selection if existing or update to first available
        if 0 < len(self._stations) > 1 and len(self._parameter_multichoice.value) > 1:
            self._parameter_multichoice.value = self._parameter_multichoice.value[:1]
        elif not self._parameter_multichoice.value:
            self._parameter_multichoice.value = available_params[:1]
            self._selected_parameters = available_params[:1]

        # self._selected_parameters = self._parameter_multichoice.value

        self._update_series()

        self._load_series()
        # Trigger actual series update
        # self._on_parameters_changed(None, None, default_params)

    def _on_parameters_changed(self, attr, old, new):
        """
        Called when MultiChoice selection changes.
        Rebuilds series list and reloads glyphs.
        """
        selected_parameters = new
        if not self._stations or not selected_parameters:
            return

        # If multiple stations → force single parameter
        if len(self._stations) > 1:
            selected_parameters = selected_parameters[:1]
        self._selected_parameters = selected_parameters

        self._update_series()

        # Load new series into figure
        self._load_series()

    def _load_series(self):
        # clear old
        print("load series")
        # self._figure.renderers = []  # or selectively remove only series glyphs
        active_keys = set()

        for spec in self._series:
            print(f"plot {spec.parameter} from {spec.station.name}")
            key = (spec.station.visit_key, spec.parameter)
            active_keys.add(key)
            if key in self._series_glyphs:
                # already plotted → skip adding glyphs again
                continue

            # build sources to populate
            main_source = self._make_data_source()
            stats_source = self._make_statistics_source()

            df, has_data = self._fetch_data(spec)
            print("data fetched")
            if not has_data:
                print(
                    f"Did not find any data for {spec.parameter} at {spec.station.name}"
                )
                continue
            print("transform data")
            records = self._transform_data(spec, df)
            print("populate source")
            self._populate_source(main_source, records)
            print("fetch stats")
            stats = self._fetch_statistics(spec)
            if stats:
                stats_source.data = stats
            print("add glyphs")
            self._add_glyphs(spec, main_source, stats_source)
            print("add series sources")
            # store for reference in next update
            self._series_sources[key] = {
                "main": main_source,
                "stats": stats_source,
            }

        # remove anything that's no longer in self._series
        print("remove unused series")
        self._remove_unused_series(active_keys)

        # Now update the ocean floor based on loaded stations
        self._update_ocean_floor()

    def _remove_unused_series(self, active_keys: set):
        """
        Remove glyphs and sources that are no longer active.
        """
        to_remove = set(self._series_glyphs.keys()) - active_keys

        for key in to_remove:
            glyphs = self._series_glyphs.pop(key, {})
            for g in glyphs.values():
                try:
                    self._figure.renderers.remove(g)
                except ValueError:
                    pass  # already removed

            self._series_sources.pop(key, None)

    def _fetch_data(self, spec: SeriesSpecification):
        print(f"fetch data for parameter: {spec.parameter}")
        print(
            spec.station.data.filter(pl.col("parameter") == spec.parameter).select(
                ["DEPH", "parameter", "value"]
            )
        )

        # Filter lazy dataframe for the parameter
        df = spec.station.data.filter(pl.col("parameter") == spec.parameter).sort("DEPH")

        # Check if any rows exist by limiting to 1 row
        has_data = not df.limit(1).is_empty()

        return df, has_data

    def _transform_data(self, spec: SeriesSpecification, df):
        """
        Takes series object and the data from the series object
        Returns data as dict in list to add to all_records
        """
        qc_flags = list(map(QcFlags.from_string, df["quality_flag_long"]))
        colors = [QC_FLAG_CSS_COLORS.get(flag.total) for flag in qc_flags]
        line_colors = [
            "black" if f.incoming.value != f.total.value else "none" for f in qc_flags
        ]

        return [
            dict(
                x=row["value"],
                y=row["DEPH"],
                color=color,
                line_color=lcolor,
                qc=f"{flags.total} ({flags.total.value})",
                qc_incoming=f"{flags.incoming} ({flags.incoming.value})",
                qc_automatic=f"{flags.total_automatic} {flags.total_automatic_name}",
                qc_manual=f"{flags.manual} ({flags.manual.value})",
                series_label=f"{spec.parameter} @ {spec.station.name}",
            )
            for row, flags, color, lcolor in zip(
                df.iter_rows(named=True), qc_flags, colors, line_colors
            )
        ]

    def _fetch_statistics(self, spec: SeriesSpecification) -> Optional[dict[str, list]]:
        """Fetch statistics for one series (parameter + station)."""
        station = spec.station
        if station.sea_basin is None:
            return None

        stats = statistic.get_profile_statistics_for_parameter_and_sea_basin(
            spec.parameter,
            station.sea_basin,
            station.datetime,
            statistics=("median", "25p", "75p", "min", "max"),
        )

        if stats is None:
            return None

        stats_df = pd.DataFrame(stats)

        # Filter depths to within 110% of station water depth
        filtered = stats_df[stats_df["depth"] <= station.water_depth * 1.1]

        return {
            "depth": filtered["depth"].tolist(),
            "median": filtered["median"].tolist(),
            "lower_limit": filtered["25p"].tolist(),
            "upper_limit": filtered["75p"].tolist(),
            "min": filtered["min"].tolist(),
            "max": filtered["max"].tolist(),
        }

    def _populate_source(self, source: ColumnDataSource, records: list[dict]):
        if not records:
            source.data = {k: [] for k in source.data.keys()}
            return
        columns = {key: [rec[key] for rec in records] for key in records[0]}
        source.data = columns

    def _add_glyphs(
        self,
        spec: SeriesSpecification,
        source: ColumnDataSource,
        stats_source: ColumnDataSource,
    ):
        key = (
            spec.station.visit_key,
            spec.parameter,
        )
        # Skip if the series is already added
        if key in self._series_glyphs:
            return
        if key not in self._series_keys:
            self._series_keys.append(key)

        # Add values and lines
        _lines = self._figure.line("x", "y", source=source, **self._plot_line_config)

        _parameter_values = self._figure.scatter(
            "x",
            "y",
            source=source,
            color="color",
            line_color="line_color",
            # legend_label=f"{spec.parameter} @ {spec.station.name}",
            **self._plot_values_config,
        )

        self._hover_renderers.append(_parameter_values)

        # Add statistics glyphs
        _median_values_line = self._figure.line(
            "median",
            "depth",
            source=stats_source,
            **self._plot_line_statistics_config,
        )
        _median_values_dash = self._figure.scatter(
            "median",
            "depth",
            marker="dash",
            source=stats_source,
            **self._plot_dash_statistics_config,
        )
        _limits_area = self._figure.harea(
            x1="lower_limit",
            x2="upper_limit",
            y="depth",
            source=stats_source,
            **self._plot_area_statistics_config,
        )
        _min_line = self._figure.line(
            "min",
            "depth",
            source=stats_source,
            **self._plot_line_min_max_config,
        )
        _max_line = self._figure.line(
            "max",
            "depth",
            source=stats_source,
            **self._plot_line_min_max_config,
        )

        self._series_glyphs[key] = {
            "values": _parameter_values,
            "line": _lines,
            "median_line": _median_values_line,
            "median_dash": _median_values_dash,
            "limits_area": _limits_area,
            "min_line": _min_line,
            "max_line": _max_line,
        }
        self._series_sources[key] = {
            "values": source,
            "statistics": stats_source,
        }

        # Update hover tool
        self._hover_tool.renderers = (
            self._hover_renderers
        )  # move this to after add_glyphs call

    def _value_selected(self, attr, old, new, series_spec: SeriesSpecification):
        """
        attr, old, new: standard Bokeh selected callback args
        series_spec: which series in this slot triggered the selection
        """
        selected_indices = self._series_sources[series_spec][0].selected.indices
        selected_values = [
            self._series_sources[series_spec][0].data["x"][i] for i in selected_indices
        ]
        # Call the main callback with slot and series
        self._value_selected_callback(selected_values, self, series_spec)

    def _update_ocean_floor(self):
        """
        Update ocean floor depth based on max WADEP of all stations in current series.
        """
        if not self._series:
            return

        # Collect valid WADEP values
        water_depth_values = [
            getattr(spec.station, "water_depth", None)
            for spec in self._series
            if getattr(spec.station, "water_depth", None) is not None
        ]

        if not water_depth_values:
            # No valid WADEP values found, fall back to a default
            self._ocean_floor.bottom = 10
            self._ocean_floor.top = 12  # arbitrary safe default
            return

        max_water_depth = max(water_depth_values)

        # Set bottom of ocean floor to max WADEP and extend with 2 % + 1 m
        self._ocean_floor.bottom = max_water_depth
        self._ocean_floor.top = max_water_depth * 1.02 + 1

    @property
    def layout(self):
        return column(self._parameter_multichoice, self._figure)


class ProfileSlot(Layoutable):
    def __init__(
        self,
        parameter: str | None = None,
        linked_parameter: Self | None = None,
        value_selected_callback=None,
    ):
        self._value_selected_callback = value_selected_callback or (lambda *args: None)
        self._clear_called = False
        self._width = 375
        self._height = 500
        self._parameter = parameter
        self._station: Station = None
        self._parameter_data = None
        self._source = ColumnDataSource(
            data={
                "x": [],
                "y": [],
                "color": [],
                "line_color": [],
                "QC": [],
                "qc_incoming": [],
                "qc_automatic": [],
                "qc_manual": [],
            }
        )

        self._statistics_source = ColumnDataSource(
            data={
                "depth": [],
                "median": [],
                "lower_limit": [],
                "upper_limit": [],
                "min": [],
                "max": [],
            }
        )

        self._parameter_options = ParameterOptions()

        self._primary_plot = linked_parameter is None
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
        select = LassoSelectTool()
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
                ("Value", "@x"),
                ("Depth", "@y"),
                ("QC", "@qc"),
                ("Incoming QC", "@qc_incoming"),
                ("Automatic QC", "@qc_automatic"),
                ("Manual QC", "@qc_manual"),
            ],
            "y_axis_label": "Depth [m]",
        }
        self._plot_values_config = {
            "size": 8,
            "alpha": 0.8,
            "name": "values",
        }
        self._plot_line_config = {
            "line_width": 1,
            "color": "navy",
            "alpha": 0.8,
            "name": "connecting_line",
        }
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
        self._plot_line_min_max_config = {"color": "red", "line_width": 0.5, "alpha": 0.5}
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

        # Add values and lines
        self._lines = self._figure.line(
            "x", "y", source=self._source, **self._plot_line_config
        )

        self._parameter_values = self._figure.scatter(
            "x",
            "y",
            source=self._source,
            color="color",
            line_color="line_color",
            **self._plot_values_config,
        )

        self._parameter_values.data_source.selected.on_change(
            "indices", self._value_selected
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
        self.clear_selection()
        self._station = station
        self._parameter_dropdown.menu = [
            (expand_abbreviation(parameter), parameter)
            for parameter in self._station.parameters
        ]
        self._source.data = {
            "x": [],
            "y": [],
            "color": [],
            "line_color": [],
            "qc": [],
            "qc_incoming": [],
            "qc_automatic": [],
            "qc_manual": [],
        }

        self._statistics_source.data = {
            "depth": [],
            "median": [],
            "lower_limit": [],
            "upper_limit": [],
            "min": [],
            "max": [],
        }

        if self._parameter in self._station.parameters:
            self._load_parameter()
            self._no_data_label.visible = False
        else:
            self._no_data_label.visible = True

        self._ocean_floor.top = self._station.water_depth
        self._sync_parameter_options()

    def clear_selection(self):
        self._clear_called = True
        self._source.selected.indices = []
        self._clear_called = False

    def set_parameter(self, parameter: str):
        self._parameter = parameter
        self._load_parameter()

    def _parameter_selected(self, event: MenuItemClick):
        self._parameter = event.item

    def _value_selected(self, attr, old, new):
        selected_values = [
            Parameter(self._parameter_data.row(n, named=True)) for n in new
        ]
        self._statistics_source.selected.indices = []
        if not self._clear_called:
            self._value_selected_callback(selected_values, self)

    def _load_parameter(self):
        self._parameter_data = self._station.data.filter(
            pl.col("parameter") == self._parameter
        ).sort("DEPH")

        if "quality_flag_long" not in self._parameter_data.columns:
            try:
                self._parameter_data["quality_flag_long"] = self._parameter_data[
                    "quality_flag"
                ].map(lambda x: str(QcFlags(QcFlag.parse(x), None, None, None)))
            except FileExistsError:
                print("OJOJOJOJOJ DUM EXCEPT!!!!!!!")
                print(self._parameter)
                raise

        self._parameter_data = self._parameter_data.with_columns(
            quality_flag=pl.struct("quality_flag_long").map_elements(
                lambda row: QcFlags.from_string(row["quality_flag_long"]).total,
                return_dtype=pl.Int8,
            )
        )

        qc_flags = list(
            map(QcFlags.from_string, self._parameter_data["quality_flag_long"])
        )

        colors = list(
            map(QC_FLAG_CSS_COLORS.get, list(self._parameter_data["quality_flag"]))
        )

        line_colors = [
            "black" if flags.incoming.value != flags.total.value else "none"
            for flags in qc_flags
        ]

        if self._station.sea_basin is None:
            parameter_statistics = None
        else:
            parameter_statistics = (
                statistic.get_profile_statistics_for_parameter_and_sea_basin(
                    self._parameter,
                    self._station.sea_basin,
                    self._station.datetime,
                    statistics=("median", "25p", "75p", "min", "max"),
                )
            )
        self._update_statistics(parameter_statistics=parameter_statistics)

        self._source.data = {
            "x": list(self._parameter_data["value"]),
            "y": list(self._parameter_data["DEPH"]),
            "color": colors,
            "line_color": line_colors,
            "qc": [f"{flags.total} ({flags.total.value})" for flags in qc_flags],
            "qc_incoming": [
                f"{flags.incoming} ({flags.incoming.value})" for flags in qc_flags
            ],
            "qc_automatic": [
                f"{flags.total_automatic} {flags.total_automatic_name}"
                for flags in qc_flags
            ],
            "qc_manual": [f"{flags.manual} ({flags.manual.value})" for flags in qc_flags],
        }

        self._parameter_dropdown.label = expand_abbreviation(self._parameter)

    def _update_statistics(self, parameter_statistics):
        if parameter_statistics is None:
            self._statistics_source.data = {}
            return

        # Convert the statistical data to a DataFrame for easier filtering
        stats_df = pd.DataFrame(parameter_statistics)

        # Filter rows where 'depth' is less than or equal to self._station.water_depth
        filtered_stats = stats_df[stats_df["depth"] <= self._station.water_depth * 1.1]

        # Update the Bokeh data source with the filtered statistics
        self._statistics_source.data = {
            "depth": filtered_stats["depth"].tolist(),
            "median": filtered_stats["median"].tolist(),
            "lower_limit": filtered_stats["25p"].tolist(),
            "upper_limit": filtered_stats["75p"].tolist(),
            "min": filtered_stats["min"].tolist(),
            "max": filtered_stats["max"].tolist(),
        }

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
