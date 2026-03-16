import typing

from qc_tool.models.manual_qc_model import ManualQcModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.filtered_profiles_controller import (
        FilteredProfilesController,
    )

import polars as pl
from bokeh.models import Column, Row
from ocean_data_qc import statistic
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flags import QcFlags

from qc_tool.filtered_profiles_slot import FilteredProfilesSlot
from qc_tool.models.filter_model import FilterModel
from qc_tool.models.filtered_profiles_model import FilteredProfilesModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.base_view import BaseView


class FilteredProfilesView(BaseView):
    def __init__(
        self,
        controller: "FilteredProfilesController",
        filtered_profiles_model: FilteredProfilesModel,
        filter_model: FilterModel,
        visits_model: VisitsModel,
        manual_qc_model: ManualQcModel,
    ):
        self._controller = controller
        self._controller.filtered_profiles_view = self

        self._filtered_profiles_model = filtered_profiles_model
        self._filter_model = filter_model
        self._visits_model = visits_model
        self._manual_qc_model = manual_qc_model

        self._columns = 5
        self._rows = 2

        self._profiles = []
        self._column = Column(children=[], sizing_mode="stretch_both")

        self._build_grid()
        self._parameter_data = {}
        self._background_data = None

    @property
    def layout(self):
        return self._column

    def _build_grid(self):
        total_profiles = self._rows * self._columns
        self._primary_plot = FilteredProfilesSlot(
            manual_qc_model=self._manual_qc_model,
            filtered_profiles_model=self._filtered_profiles_model,
            profile_index=0,
        )
        self._profiles.append(self._primary_plot)
        for i in range(total_profiles - 1):
            self._profiles.append(
                FilteredProfilesSlot(
                    manual_qc_model=self._manual_qc_model,
                    filtered_profiles_model=self._filtered_profiles_model,
                    linked_plot=self._primary_plot,
                    profile_index=i,
                )
            )

        for n in range(self._rows):
            start = n * self._columns
            end = start + self._columns
            row = Row(children=[profile.layout for profile in self._profiles[start:end]])
            self._column.children.append(row)

    def update_grid_content(self, flag: str):
        if self._visits_model.selected_visit is None:
            return
        for i, profile in enumerate(self._profiles):
            if profile._parameter == "":
                profile.clear_figure()
                profile._parameter_dropdown.menu = (
                    self._visits_model.selected_visit.parameters
                )
            else:
                if (
                    flag == "parameter"
                    and profile._profile_index
                    != self._filtered_profiles_model.selected_profile_index
                ):
                    continue
                parameter_data, parameter_statistics = self._load_parameter(
                    profile._parameter
                )
                if parameter_data is None:
                    profile.clear_figure()
                else:
                    profile.set_data(
                        (profile._parameter, parameter_data)
                        if profile._parameter
                        else [],
                        self._visits_model.selected_visit,
                    )
                    profile.set_filtered_data(
                        self._load_filtered_data(profile._parameter)
                    )
                    if self._visits_model.selected_visit:
                        water_depth = (
                            self._visits_model.selected_visit.water_depth
                            if self._visits_model.selected_visit.water_depth is not None
                            else self._visits_model.selected_visit.max_depth
                        )
                    else:
                        water_depth = None
                    profile.update_statistics(
                        parameter_statistics=parameter_statistics,
                        water_depth=water_depth,
                    )
                    profile._sync_y_axis()
                profile._parameter_dropdown.menu = (
                    self._visits_model.selected_visit.parameters
                )

    def _load_parameter(self, parameter):
        if self._visits_model.selected_visit is not None:
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
                    lambda row: QcFlags.from_string(row["quality_flag_long"]).total.value,
                    return_dtype=pl.Utf8,
                )
            )
            qc_flags = list(map(QcFlags.from_string, parameter_data["quality_flag_long"]))

            colors = [
                QC_FLAG_CSS_COLORS.get(QcFlag.parse(flag))
                for flag in parameter_data["quality_flag"]
            ]

            line_colors = [
                "black" if flags.incoming.value != flags.total.value else "none"
                for flags in qc_flags
            ]

            if parameter_data.is_empty():
                source_data = None
            else:
                source_data = {
                    "x": list(parameter_data["value"]),
                    "unit": list(parameter_data["unit"]),
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

            if None in (self._visits_model.selected_visit.sea_basin, source_data):
                parameter_statistics = None
            else:
                statistics_parameter = parameter

                parameter_statistics = (
                    statistic.get_profile_statistics_for_parameter_and_sea_basin(
                        statistics_parameter,
                        self._visits_model.selected_visit.sea_basin,
                        self._visits_model.selected_visit.datetime,
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
            self._parameter_data[parameter] = (
                source_data,
                parameter_statistics,
            )

        return self._parameter_data.get(parameter, (None, None))

    def _load_filtered_data(self, parameter):
        if self._filter_model.filtered_data.is_empty():
            return None

        data = self._filter_model.filtered_data.filter(
            (pl.col("parameter") == parameter)
            & (
                pl.col("DEPH") <= self._visits_model.selected_visit.water_depth
                if self._visits_model.selected_visit.water_depth is not None
                else pl.lit(True)
            )
        ).sort("DEPH")

        if data.is_empty():
            return None

        return {
            "x": list(data["value"]),
            "y": list(data["DEPH"]),
        }
