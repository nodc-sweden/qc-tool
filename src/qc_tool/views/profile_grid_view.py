import typing

from qc_tool.models.manual_qc_model import ManualQcModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.profile_grid_controller import ProfileGridController

import polars as pl
from bokeh.models import Column, Row
from ocean_data_qc import statistic
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flags import QcFlags

from qc_tool.models.parameters_model import ParametersModel
from qc_tool.models.profiles_grid_model import ProfileGridModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.profile_slot import ProfileSlot
from qc_tool.views.base_view import BaseView


class ProfileGridView(BaseView):
    def __init__(
        self,
        controller: "ProfileGridController",
        profile_grid_model: ProfileGridModel,
        parameters_model: ParametersModel,
        visits_model: VisitsModel,
        manual_qc_model: ManualQcModel,
    ):
        self._controller = controller
        self._controller.profile_grid_view = self

        self._profile_grid_model = profile_grid_model
        self._parameters_model = parameters_model
        self._visits_model = visits_model
        self._manual_qc_model = manual_qc_model

        # Persistent layout container to allow dynamic, in-place updates
        self._profiles = []
        self._primary_plot = None

        self._column = Column(children=[], sizing_mode="stretch_both")

        self.update_grid_size()

    @property
    def plot_rows(self):
        return self._column.children

    @plot_rows.setter
    def plot_rows(self, rows):
        self._column.children = rows

    def update_grid_size(self):
        """Syncs layout with the correct rows and columns."""
        if not self._profiles:
            self._primary_plot = ProfileSlot(
                manual_qc_model=self._manual_qc_model,
                value_selected_callback=self._value_selected,
            )
            self._profiles.append(self._primary_plot)

        if len(self._profiles) < self._profile_grid_model.number_of_profiles:
            # Too few profiles, creating new.
            for _ in range(
                self._profile_grid_model.number_of_profiles - len(self._profiles)
            ):
                self._profiles.append(
                    ProfileSlot(
                        manual_qc_model=self._manual_qc_model,
                        linked_plot=self._primary_plot,
                        value_selected_callback=self._value_selected,
                    )
                )
        elif len(self._profiles) > self._profile_grid_model.number_of_profiles:
            # Too many profiles, removing extra.
            self._profiles = self._profiles[: self._profile_grid_model.number_of_profiles]

        for n, row in enumerate(self.plot_rows):
            if len(row.children) != self._profile_grid_model.columns:
                # Wrong column width for row, recreating from profiles
                start = n * self._profile_grid_model.columns
                end = start + self._profile_grid_model.columns
                row.children = [profile.layout for profile in self._profiles[start:end]]

        if len(self.plot_rows) < self._profile_grid_model.rows:
            # Too few rows, creating new
            plotted_rows = len(self.plot_rows)
            for n in range(self._profile_grid_model.rows - plotted_rows):
                start = (plotted_rows + n) * self._profile_grid_model.columns
                end = start + self._profile_grid_model.columns
                self.plot_rows.append(
                    Row(
                        children=[profile.layout for profile in self._profiles[start:end]]
                    )
                )
        elif len(self.plot_rows) > self._profile_grid_model.rows:
            # Too many rows, removing extra
            for extra_row in self.plot_rows[self._profile_grid_model.rows :]:
                self.plot_rows.remove(extra_row)
            self._profiles = self._profiles[: self._profile_grid_model.rows]

    def _value_selected(self, *args):
        print(args)

    @property
    def layout(self):
        return self._column

    def update_grid_content(self):
        empty_slots = [""] * max(
            self._profile_grid_model.number_of_profiles
            - len(self._parameters_model.selected_parameters),
            0,
        )
        parameters = self._parameters_model.selected_parameters + empty_slots

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
                    station=self._visits_model.selected_visit,
                )
            else:
                parameter_data, parameter_statistics = self._load_parameter(parameter)
                profile.set_data(
                    parameter,
                    [(parameter, parameter_data)] if parameter else [],
                    self._visits_model.selected_visit,
                )
                profile.update_statistics(
                    parameter_statistics=parameter_statistics,
                    water_depth=self._visits_model.selected_visit.water_depth
                    if self._visits_model.selected_visit
                    else None,
                )

    def _load_parameter(self, parameter):
        if (
            parameter not in self._parameters_model.parameter_data
            and self._visits_model.selected_visit is not None
        ):
            parameter_data = self._visits_model.selected_visit.data.filter(
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

            if True:#None in (self._visits_model.selected_visit.sea_basin, source_data):
                parameter_statistics = None
            else:
                # TODO
                """
                Om salt, temp, eller dox, använd nedanstående:
                SALT_CTD
                TEMP_CTD
                DOX_BTL
                OBS: även i multiplott med tex olika salt.
                OBS: Lämna tydliga spår så att det blir lätt att koppla in ny statistik
                """

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
            self._parameters_model.parameter_data[parameter] = (
                source_data,
                parameter_statistics,
            )

        return self._parameters_model.parameter_data.get(parameter, (None, None))
