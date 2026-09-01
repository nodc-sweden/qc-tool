import typing
from time import perf_counter

from qc_tool.models.manual_qc_model import ManualQcModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.profile_grid_controller import ProfileGridController

from bokeh.models import Column, Row
from ocean_data_qc import statistic

from qc_tool.models.parameters_model import ParametersModel
from qc_tool.models.profiles_grid_model import ProfileGridModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.profile_slot import ProfileSlot, SlotConfig
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
        self._profiles: list[ProfileSlot] = []
        self._primary_plot = None

        self._column = Column(children=[], sizing_mode="stretch_both")

        self.update_grid_size()

    @property
    def plot_rows(self):
        return self._column.children

    @plot_rows.setter
    def plot_rows(self, rows):
        self._column.children = rows

    def update_grid_size(self) -> int:
        """Syncs layout with the correct rows and columns.

        Returns the index of the first newly added profile, or len(_profiles)
        if no profiles were added.
        """
        if not self._profiles:
            self._primary_plot = ProfileSlot(
                manual_qc_model=self._manual_qc_model,
            )
            self._profiles.append(self._primary_plot)

        first_new = len(self._profiles)

        if len(self._profiles) < self._profile_grid_model.number_of_profiles:
            # Too few profiles, creating new.
            for _ in range(
                self._profile_grid_model.number_of_profiles - len(self._profiles)
            ):
                self._profiles.append(
                    ProfileSlot(
                        manual_qc_model=self._manual_qc_model,
                        linked_plot=self._primary_plot,
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

        return first_new

    @property
    def layout(self):
        return self._column

    def update_colors(self, updated_values):
        for profile in self._profiles:
            profile.update_colors(updated_values)

    def update_grid_content(self, start_index: int = 0):
        t0 = perf_counter()
        visit = self._visits_model.selected_visit
        if visit:
            water_depth = (
                visit.water_depth if visit.water_depth is not None else visit.max_depth
            )
            max_depth = visit.max_depth
        else:
            water_depth = None
            max_depth = None

        empty_slots = [""] * max(
            self._profile_grid_model.number_of_profiles
            - len(self._parameters_model.selected_parameters),
            0,
        )
        requested_slot_parameters = (
            self._parameters_model.selected_parameters + empty_slots
        )
        for n, (slot, parameters) in enumerate(
            zip(self._profiles, requested_slot_parameters)
        ):
            configuration = self._get_slot_configuration(parameters)
            slot._configuration = configuration

            if n < start_index:
                continue
            slot_data = []
            for parameter in slot._configuration.parameters:
                parameter_data = self._get_parameter_data(parameter)
                slot_data.append(
                    (
                        parameter,
                        parameter_data,
                        visit.ctd_data_for_parameter(parameter),
                    )
                )
            slot.set_data(
                title=parameters,
                data=slot_data,
                max_depth=max_depth,
                water_depth=water_depth,
            )
            statistics_parameter = self._get_statistics_parameter(
                slot._configuration.parameters
            )
            parameter_statistics = (
                self._get_parameter_statistics(statistics_parameter)
                if slot.has_data
                else None
            )
            slot.update_statistics(
                parameter_statistics=parameter_statistics,
                water_depth=water_depth,
            )
        print(
            f"ProfileGridView.update_grid_content {n - start_index}",
            f"slots in {perf_counter() - t0:.4f} sec",
        )

    def _get_parameter_data(self, parameter):
        visit = self._visits_model.selected_visit

        if visit is None:
            return None

        return visit.parameter_data(parameter)

    def _get_parameter_statistics(self, parameter):
        visit = self._visits_model.selected_visit

        if visit is None:
            return None
        if None in (visit.sea_basin, visit.datetime):
            return None

        parameter_statistics = (
            statistic.get_profile_statistics_for_parameter_and_sea_basin(
                parameter,
                visit.sea_basin,
                visit.datetime,
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

        return parameter_statistics

    def _get_statistics_parameter(self, parameter_components):
        if len(parameter_components) == 1:
            return parameter_components[0]

        if len(parameter_components) != 2:
            return None

        bases = {
            parameter.removesuffix("_CTD").removesuffix("_BTL")
            for parameter in parameter_components
        }

        if len(bases) == 1:
            return bases.pop().lower()

        return None

    def _get_slot_configuration(self, parameter: str) -> SlotConfig:
        if not parameter:
            return SlotConfig(())

        components = tuple(component.strip() for component in parameter.split("+"))

        return SlotConfig(components)
