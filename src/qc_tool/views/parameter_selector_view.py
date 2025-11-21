import typing

from qc_tool.models.profiles_grid_model import ProfileGridModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.parameter_selector_controller import (
        ParameterSelectorController,
    )

from bokeh.layouts import column, row
from bokeh.models import Button, MultiSelect, Spacer, Spinner, TablerIcon, UIElement

from qc_tool.models.parameters_model import ParametersModel
from qc_tool.views.base_view import BaseView


class ParameterSelectorView(BaseView):
    def __init__(
        self,
        controller: "ParameterSelectorController",
        parameters_model: ParametersModel,
        profile_grid_model: ProfileGridModel,
    ):
        self._controller = controller
        self._controller.parameter_selector_view = self

        self._parameters_model = parameters_model
        self._profile_grid_model = profile_grid_model

        self._available_parameters_select = MultiSelect(
            title="Available parameters", size=10, width=200
        )

        self._available_multi_parameters_select = MultiSelect(
            title="Available multi parameters", size=10, width=200
        )

        self._selected_parameters = MultiSelect(
            title="Selected parameters", size=20, width=250
        )

        self._rows_input = Spinner(
            value=self._profile_grid_model.rows,
            low=1,
            high=10,
            step=1,
            title="Rows",
            width=50,
        )

        self._columns_input = Spinner(
            value=self._profile_grid_model.columns,
            low=1,
            high=10,
            step=1,
            title="Columns",
            width=50,
        )

        self._init_buttons()

        self._row = row(
            column(
                self._available_parameters_select, self._available_multi_parameters_select
            ),
            column(
                Spacer(height=20),
                self._select_button,
                self._deselect_button,
                self._move_up_button,
                self._move_down_button,
                Spacer(height=20),
                self._rows_input,
                self._columns_input,
            ),
            self._selected_parameters,
        )

    def _init_buttons(self):
        self._select_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-right", size="1.2em"),
            width=80,
        )
        self._select_button.on_event("button_click", self._on_select_button_pressed)

        self._deselect_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-left", size="1.2em"),
            width=80,
        )
        self._deselect_button.on_event("button_click", self._on_deselect_button_pressed)

        self._move_up_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-up", size="1.2em"),
            width=80,
        )
        self._move_up_button.on_event("button_click", self._on_move_up_button_pressed)

        self._move_down_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-down", size="1.2em"),
            width=80,
        )
        self._move_down_button.on_event("button_click", self._on_move_down_button_pressed)

        self._rows_input.on_change("value", self._on_rows_changed)
        self._columns_input.on_change("value", self._on_columns_changed)
        self._available_multi_parameters_select.on_change(
            "value", self._on_available_multi_parameters_selected
        )
        self._available_parameters_select.on_change(
            "value", self._on_available_parameters_selected
        )

    def _on_select_button_pressed(self):
        selection = (
            self._available_parameters_select.value
            + self._available_multi_parameters_select.value
        )
        self._controller.select_parameters(selection)

    def _on_deselect_button_pressed(self):
        selection = set(self._selected_parameters.value)
        self._controller.deselect_parameters(selection)

    def _on_move_up_button_pressed(self):
        selection = set(self._selected_parameters.value)
        self._controller.move_selection_up(selection)

    def _on_move_down_button_pressed(self):
        selection = set(self._selected_parameters.value)
        self._controller.move_selection_down(selection)

    def _on_rows_changed(self, attr, old, new):
        self._controller.set_rows(new)

    def _on_columns_changed(self, attr, old, new):
        self._controller.set_columns(new)

    def _on_available_multi_parameters_selected(self, attr, old, new):
        self._available_parameters_select.value = []

    def _on_available_parameters_selected(self, attr, old, new):
        self._available_multi_parameters_select.value = []

    def update_parameters(self):
        self._available_parameters_select.options = (
            self._parameters_model.available_parameters
        )
        self._available_multi_parameters_select.options = (
            self._parameters_model.available_multiparameters
        )
        self._selected_parameters.options = self._parameters_model.selected_parameters
        self.sync_button_state()

    def sync_button_state(self):
        enabled = self._parameters_model.enabled
        self._select_button.disabled = not (
            enabled
            and (
                self._profile_grid_model.number_of_profiles
                > self._parameters_model.selection_size
            )
        )
        self._deselect_button.disabled = not enabled
        self._move_up_button.disabled = not enabled
        self._move_down_button.disabled = not enabled

    @property
    def layout(self) -> UIElement:
        return self._row

    def clear_all_selections(self):
        self._available_parameters_select.value = []
        self._available_multi_parameters_select.value = []
        self._selected_parameters.value = []
