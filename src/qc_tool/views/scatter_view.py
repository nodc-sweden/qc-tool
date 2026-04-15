import typing

from qc_tool.models.manual_qc_model import ManualQcModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.scatter_controller import (
        ScatterController,
    )

import polars as pl
from bokeh.models import Column, Row
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flags import QcFlags

from qc_tool.models.filter_model import FilterModel
from qc_tool.models.scatter_model import ScatterModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.scatter_slot import ScatterSlot
from qc_tool.views.base_view import BaseView


class ScatterView(BaseView):
    def __init__(
        self,
        controller: "ScatterController",
        scatter_model: ScatterModel,
        filter_model: FilterModel,
        visits_model: VisitsModel,
        manual_qc_model: ManualQcModel,
    ):
        self._controller = controller
        self._controller.scatter_view = self

        self._scatter_model = scatter_model
        self._filter_model = filter_model
        self._visits_model = visits_model
        self._manual_qc_model = manual_qc_model

        self._columns = 5
        self._rows = 2

        self._scatters = []
        self._column = Column(children=[], sizing_mode="stretch_both")

        self._build_grid()
        self._parameter_data = {}
        self._background_data = None

    @property
    def layout(self):
        return self._column

    def _build_grid(self):
        total_scatters = self._rows * self._columns
        self._primary_plot = ScatterSlot(
            manual_qc_model=self._manual_qc_model,
            scatter_model=self._scatter_model,
            scatter_index=0,
        )
        self._scatters.append(self._primary_plot)
        for i in range(total_scatters - 1):
            self._scatters.append(
                ScatterSlot(
                    manual_qc_model=self._manual_qc_model,
                    scatter_model=self._scatter_model,
                    scatter_index=i,
                )
            )

        for n in range(self._rows):
            start = n * self._columns
            end = start + self._columns
            row = Row(children=[scatter.layout for scatter in self._scatters[start:end]])
            self._column.children.append(row)

    def update_colors(self, updated_values):
        for scatter in self._scatters:
            scatter.update_colors(updated_values)

    def update_grid_content(self, flag: str):
        if self._visits_model.selected_visit is None:
            return
        for i, scatter in enumerate(self._scatters):
            if not scatter.x_parameter or not scatter.y_parameter:
                scatter.clear_figure()
                scatter._x_parameter_dropdown.menu = (
                    self._visits_model.selected_visit.parameters
                )
                scatter._y_parameter_dropdown.menu = (
                    self._visits_model.selected_visit.parameters
                )
            else:
                if (
                    flag == "parameter"
                    and scatter.scatter_index
                    != self._scatter_model.selected_scatter_index
                ):
                    continue
                source_data, merged_data = self._load_parameters(
                    scatter.x_parameter, scatter.y_parameter
                )
                if merged_data is None:
                    scatter.clear_figure()
                else:
                    scatter.set_data(
                        scatter.x_parameter,
                        scatter.y_parameter,
                        source_data,
                        merged_data,
                        self._visits_model.selected_visit,
                    )
                    scatter.set_filtered_data(
                        self._load_filtered_data(scatter.x_parameter, scatter.y_parameter)
                    )

                scatter._x_parameter_dropdown.menu = (
                    self._visits_model.selected_visit.parameters
                )
                scatter._y_parameter_dropdown.menu = (
                    self._visits_model.selected_visit.parameters
                )

    def _load_parameters(self, x_parameter, y_parameter):
        if self._visits_model.selected_visit is None:
            self._parameter_data = None, None
            return self._parameter_data

        merged_data = (
            self._visits_model.selected_visit.data.filter(
                pl.col("parameter").is_in([x_parameter, y_parameter])
                & pl.col("value").is_not_null(),
            )
            .sort("DEPH")
            .pivot(
                index="DEPH",
                columns="parameter",
                values=["value", "unit", "quality_flag", "quality_flag_long"],
            )
        )
        if (f"value_{x_parameter}" not in merged_data.columns) or (
            f"value_{y_parameter}" not in merged_data.columns
        ):
            self._parameter_data = None, None
            return self._parameter_data

        merged_data = merged_data.drop_nulls(
            [f"value_{x_parameter}", f"value_{y_parameter}"]
        )

        if merged_data.is_empty():
            self._parameter_data = None, None
            return self._parameter_data

        for param in [x_parameter, y_parameter]:
            long_col = f"quality_flag_long_{param}"
            flag_col = f"quality_flag_{param}"

            if long_col not in merged_data.columns:
                merged_data = merged_data.with_columns(
                    pl.col(flag_col)
                    .map_elements(
                        lambda x: str(QcFlags(QcFlag.parse(x), None, None, None)),
                        return_dtype=pl.Utf8,
                    )
                    .alias(long_col)
                )

            merged_data = merged_data.with_columns(
                pl.struct(long_col)
                .map_elements(
                    lambda row: QcFlags.from_string(row[long_col]).total.value,
                    return_dtype=pl.Utf8,
                )
                .alias(flag_col)
            )

        qc_flags_x = list(
            map(QcFlags.from_string, merged_data[f"quality_flag_long_{x_parameter}"])
        )
        qc_flags_y = list(
            map(QcFlags.from_string, merged_data[f"quality_flag_long_{y_parameter}"])
        )

        colors = [QC_FLAG_CSS_COLORS.get(flags.total) for flags in qc_flags_x]

        line_colors = [
            "black" if flags.incoming.value != flags.total.value else "none"
            for flags in qc_flags_x
        ]

        source_data = {
            "x_name": [x_parameter] * len(merged_data[f"value_{x_parameter}"]),
            "x": list(merged_data[f"value_{x_parameter}"]),
            "x_unit": list(merged_data[f"unit_{x_parameter}"]),
            "y_name": [y_parameter] * len(merged_data[f"value_{y_parameter}"]),
            "y": list(merged_data[f"value_{y_parameter}"]),
            "y_unit": list(merged_data[f"unit_{y_parameter}"]),
            "depth": list(merged_data["DEPH"]),
            "color": colors,
            "line_color": line_colors,
            "qcx": [f"{flags.total} ({flags.total.value})" for flags in qc_flags_x],
            "qcy": [f"{flags.total} ({flags.total.value})" for flags in qc_flags_y],
        }

        self._parameter_data = source_data, merged_data
        return self._parameter_data

    def _load_filtered_data(self, x_parameter, y_parameter):
        if self._filter_model.filtered_data.is_empty():
            return None

        df = self._filter_model.filtered_data.select(
            ["row_number", "parameter", "value"]
        ).filter(
            pl.col("parameter").is_in([x_parameter, y_parameter])
            & pl.col("value").is_not_null()
        )
        if not (
            {x_parameter, y_parameter}
            <= set(df.get_column("parameter").unique().to_list())
        ):
            return None

        df = df.pivot(
            index="row_number",
            columns="parameter",
            values="value",
        ).drop_nulls([x_parameter, y_parameter])

        if (
            df.is_empty()
            or x_parameter not in df.columns
            or y_parameter not in df.columns
        ):
            return None

        df = df

        return {
            "x": df[x_parameter].to_list(),
            "y": df[y_parameter].to_list(),
        }
