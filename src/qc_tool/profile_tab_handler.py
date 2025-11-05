import polars as pl
from bokeh.models import Column, Row
from ocean_data_qc import statistic
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flags import QcFlags

from qc_tool.layoutable import Layoutable
from qc_tool.new_profile_slot import NewProfileSlot
from qc_tool.parameter_handler import ParameterHandler

MULTI_PARAMETERS = [
    ("SALT_CTD", "SALT_BTL"),
    ("TEMP_CTD", "TEMP_BTL"),
    ("SALT_CTD", "TEMP_CTD"),
    ("DOXY_CTD", "DOXY_BTL"),
    ("DOXY_CTD", "DOXY_BTL", "H2S"),
    ("AMON", "NTRA", "NTRI"),
    ("AMON", "NTRZ", "NTRI"),
    ("PTOT", "PHOS", "SIO3-SI"),
    ("NTOT", "NTRA", "AMON"),
    ("NTOT", "NTRZ", "AMON"),
    ("PHOS", "AMON", "DOXY_BTL"),
    ("ALK", "PH-TOT"),
    ("CPHL", "CHLFL", "DOXY_BTL"),
    ("CHLFL", "DOXY_CTD"),
]


class ProfileTabHandler(Layoutable):
    def __init__(
        self,
        parameter_handler: ParameterHandler,
        columns=5,
        rows=2,
        value_selected_callback=None,
    ):
        self._columns = columns
        self._rows = rows

        self._parameter_handler = parameter_handler
        self._value_selected_callback = value_selected_callback
        self._plotted_parameters = []

        self._station = None
        self._profiles = []
        self._plot_rows = []
        self._parameter_data = {}

        # Persistent layout container to allow dynamic, in-place updates
        self._column = Column(children=[], sizing_mode="stretch_both")

        self._init_grid()
        self._fill_plot_grid()

    @property
    def plot_rows(self):
        return self._column.children

    @plot_rows.setter
    def plot_rows(self, rows):
        self._column.children = rows

    def _init_grid(self):
        """Syncs layout with the correct rows and columns."""
        # Make sure that the number of selected parameters
        # is not greater than the current grid size
        self.selected_parameters = self.selected_parameters[: len(self)]

        if not self._profiles:
            self._primary_plot = NewProfileSlot(
                value_selected_callback=self._value_selected_callback
            )
            self._profiles.append(self._primary_plot)

        if len(self._profiles) < len(self):
            # Too few profiles, creating new.
            for _ in range(len(self) - len(self._profiles)):
                self._profiles.append(
                    NewProfileSlot(
                        linked_plot=self._primary_plot,
                        value_selected_callback=self._value_selected_callback,
                    )
                )

        elif len(self._profiles) < len(self):
            # Too many profiles, removing extra.
            self._profiles = self._profiles[: len(self)]

        for n, row in enumerate(self.plot_rows):
            if len(row.children) != self._columns:
                # Wrong column width for row, recreating from profiles
                start = n * self._columns
                end = start + self._columns
                row.children = [profile.layout for profile in self._profiles[start:end]]

        if len(self.plot_rows) < self._rows:
            # Too few rows, creating new
            plotted_rows = len(self.plot_rows)
            for n in range(self._rows - plotted_rows):
                start = (plotted_rows + n) * self._columns
                end = start + self._columns
                self.plot_rows.append(
                    Row(
                        children=[profile.layout for profile in self._profiles[start:end]]
                    )
                )
        elif len(self.plot_rows) > self._rows:
            # Too many rows, removing extra
            for extra_row in self.plot_rows[self._rows :]:
                self.plot_rows.remove(extra_row)
            self._profiles = self._profiles[: self._rows]

    def __len__(self):
        return self._columns * self._rows

    @property
    def available_parameters(self):
        return self._parameter_handler.available_parameters

    @available_parameters.setter
    def available_parameters(self, available_parameters: list[str]):
        self._parameter_handler.available_parameters = available_parameters

    @property
    def available_multi_parameters(self):
        return self._parameter_handler.available_multi_parameters

    def clear_other_selection(self, profile):
        for profile_slot in self._profiles:
            if profile_slot is not profile:
                profile_slot.clear_selection()

    @property
    def selected_parameters(self):
        return self._parameter_handler.selected_parameters

    @selected_parameters.setter
    def selected_parameters(self, parameters: list[str]):
        self._parameter_handler.selected_parameters = parameters[: len(self)]

    @property
    def layout(self):
        return self._column

    def _fill_plot_grid(self):
        empty_slots = [""] * max(len(self) - len(self.selected_parameters), 0)
        parameters = self.selected_parameters + empty_slots

        for n, (profile, parameter) in enumerate(zip(self._profiles, parameters)):
            if "+" in parameter:
                parameter_components = [
                    component.strip() for component in parameter.split("+")
                ]
                data = [
                    (component, self._load_parameter(component)[0])
                    for component in parameter_components
                ]
                profile.set_data(
                    parameter,
                    data,
                    station=self._station,
                )
            else:
                parameter_data, parameter_statistics = self._load_parameter(parameter)
                profile.set_data(
                    parameter,
                    [(parameter, parameter_data)] if parameter else [],
                    self._station,
                )
                profile.update_statistics(
                    parameter_statistics=parameter_statistics,
                    water_depth=self._station.water_depth if self._station else None,
                )

    def _load_parameter(self, parameter):
        if parameter not in self._parameter_data and self._station is not None:
            parameter_data = self._station.data.filter(
                pl.col("parameter") == parameter
            ).sort("DEPH")

            if "quality_flag_long" not in parameter_data.columns:
                parameter_data = parameter_data.with_columns(
                    quality_flag_long=pl.col("quality_flag").map_elements(
                        lambda x: str(QcFlags(QcFlag.parse(x), None, None, None)),
                        return_dtype=pl.Utf8,
                    )
                )

            parameter_data = parameter_data.with_columns(
                quality_flag=pl.struct("quality_flag_long").map_elements(
                    lambda row: QcFlags.from_string(row["quality_flag_long"]).total,
                    return_dtype=pl.Int8,
                )
            )

            qc_flags = list(map(QcFlags.from_string, parameter_data["quality_flag_long"]))

            colors = list(
                map(QC_FLAG_CSS_COLORS.get, list(parameter_data["quality_flag"]))
            )

            line_colors = [
                "black" if flags.incoming.value != flags.total.value else "none"
                for flags in qc_flags
            ]

            if parameter_data.is_empty():
                source_data = None
            else:
                source_data = {
                    "x": list(parameter_data["value"]),
                    "y": list(parameter_data["DEPH"]),
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
                    "qc_manual": [
                        f"{flags.manual} ({flags.manual.value})" for flags in qc_flags
                    ],
                    "data": parameter_data,
                }

            if None in (self._station.sea_basin, source_data):
                parameter_statistics = None
            else:
                parameter_statistics = (
                    statistic.get_profile_statistics_for_parameter_and_sea_basin(
                        parameter,
                        self._station.sea_basin,
                        self._station.datetime,
                        statistics=(
                            "median",
                            "25p",
                            "75p",
                            "min",
                            "max",
                            "flag2_lower",
                            "flag2_upper",
                            "flag3_lower",
                            "flag3_upper",
                        ),
                    )
                )
            self._parameter_data[parameter] = (source_data, parameter_statistics)

        return self._parameter_data.get(parameter, (None, None))

    def set_station(self, station):
        self._station = station
        self.available_parameters = self._station.parameters
        self._parameter_handler.init_multi_parameters(MULTI_PARAMETERS)
        self._parameter_data = {}
        self._parameter_handler.sync_button_state(self._station is not None)

        self._fill_plot_grid()

    def sync_profiles(self, *, columns: int, rows: int):
        if (columns, rows) != (self._columns, self._rows):
            self._columns = columns
            self._rows = rows
            self._init_grid()
            self._parameter_handler.sync_button_state()
        self._fill_plot_grid()
