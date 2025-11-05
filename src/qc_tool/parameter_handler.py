from bokeh.layouts import column, row
from bokeh.models import Button, MultiSelect, Spacer, Spinner, TablerIcon, UIElement

from qc_tool.layoutable import Layoutable

DEFAULT_PARAMETERS = [
    "SALT_CTD + SALT_BTL + TEMP_CTD + TEMP_BTL",
    "DOXY_CTD + DOXY_BTL + H2S",
    "NTOT + NTRZ + AMON",
    "PTOT + PHOS + SIO3-SI",
    "ALK + PH-TOT",
    "CPHL + CHLFL + DOXY_BTL",
]


class ParameterHandler(Layoutable):
    def __init__(self, change_callback=None, columns=5, rows=2):
        self._available_parameters = set()
        self._available_multi_parameters = set()

        self._change_callback = change_callback
        self._available_parameters_select = MultiSelect(
            title="Available parameters", size=14, width=250
        )
        self._available_multi_parameters_select = MultiSelect(
            title="Available multi parameters", size=14, width=250
        )
        self._selected = MultiSelect(title="Selected parameters", size=14, width=250)
        self._rows_input = Spinner(
            value=rows, low=1, high=10, step=1, title="Rows", width=50
        )
        self._columns_input = Spinner(
            value=columns, low=1, high=10, step=1, title="Columns", width=50
        )

        self._enabled = False
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
            self._selected,
        )

    def _init_buttons(self):
        self._select_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-right", size="1.2em"),
            width=80,
        )
        self._select_button.on_event("button_click", self.select_parameters)
        self._select_button.disabled = not self._enabled

        self._deselect_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-left", size="1.2em"),
            width=80,
        )
        self._deselect_button.on_event("button_click", self.deselect_parameters)
        self._deselect_button.disabled = not self._enabled

        self._move_up_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-up", size="1.2em"),
            width=80,
        )
        self._move_up_button.on_event("button_click", self.move_parameters_up)
        self._move_up_button.disabled = not self._enabled

        self._move_down_button = Button(
            label="",
            icon=TablerIcon(icon_name="arrow-down", size="1.2em"),
            width=80,
        )
        self._move_down_button.on_event("button_click", self.move_parameters_down)
        self._move_down_button.disabled = not self._enabled

        self._rows_input.on_change(
            "value",
            lambda attr, old, new: self._change_callback(
                columns=self._columns_input.value, rows=new
            ),
        )
        self._columns_input.on_change(
            "value",
            lambda attr, old, new: self._change_callback(
                columns=new, rows=self._rows_input.value
            ),
        )

        self._available_multi_parameters_select.on_change(
            "value", _clear_other_on_selection(self._available_parameters_select)
        )
        self._available_parameters_select.on_change(
            "value", _clear_other_on_selection(self._available_multi_parameters_select)
        )

    def reset_selection(self):
        self.selected_parameters = DEFAULT_PARAMETERS

    def select_parameters(self):
        selection = (
            self._available_parameters_select.value
            + self._available_multi_parameters_select.value
        )
        if not selection:
            return None
        if len(selection) + self.selection_size > self.max_selection:
            return None

        self._available_parameters_select.value = []
        self._available_multi_parameters_select.value = []

        self.selected_parameters += selection
        self._change_callback(
            columns=self._columns_input.value,
            rows=self._rows_input.value,
        )

    def deselect_parameters(self):
        selection = set(self._selected.value)
        if not selection:
            return None
        self._selected.value = []
        self.selected_parameters = [
            parameter
            for parameter in self.selected_parameters
            if parameter not in selection
        ]
        self._change_callback(
            columns=self._columns_input.value,
            rows=self._rows_input.value,
        )

    def move_parameters_up(self):
        selection = set(self._selected.value)
        if not selection:
            return None

        new_selected = self._selected.options[:]
        for n, v in enumerate(new_selected[1:], start=1):
            if v in selection and new_selected[n - 1] not in selection:
                new_selected[n - 1], new_selected[n] = (
                    new_selected[n],
                    new_selected[n - 1],
                )
        self.selected_parameters = new_selected
        self._change_callback(
            columns=self._columns_input.value,
            rows=self._rows_input.value,
        )

    def move_parameters_down(self):
        selection = set(self._selected.value)
        if not selection:
            return None

        new_selected = self._selected.options[:]
        for n, v in reversed(list(enumerate(new_selected[:-1]))):
            if v in selection and new_selected[n + 1] not in selection:
                new_selected[n], new_selected[n + 1] = (
                    new_selected[n + 1],
                    new_selected[n],
                )
        self.selected_parameters = new_selected
        self._change_callback(
            columns=self._columns_input.value,
            rows=self._rows_input.value,
        )

    @property
    def max_selection(self) -> int:
        return self._rows_input.value * self._columns_input.value

    @property
    def selection_size(self) -> int:
        return len(self._selected.options)

    @property
    def available_parameters(self) -> list[str]:
        return sorted(self._available_parameters - set(self.selected_parameters))

    @available_parameters.setter
    def available_parameters(self, available_parameters: list[str]):
        self._available_parameters = set(available_parameters)
        self._available_parameters_select.options = self.available_parameters

    @property
    def available_multi_parameters(self) -> list[str]:
        return sorted(self._available_multi_parameters - set(self.selected_parameters))

    def init_multi_parameters(self, multi_parameters: list[tuple[str, ...]]):
        available_multi_parameters = set()
        for parameters in multi_parameters:
            if set(parameters).issubset(self._available_parameters):
                available_multi_parameters.add(" + ".join(parameters))
        self._available_multi_parameters = available_multi_parameters

    @property
    def selected_parameters(self) -> list[str]:
        return self._selected.options

    @selected_parameters.setter
    def selected_parameters(self, parameters: list[str]):
        self._selected.options = parameters
        self._available_parameters_select.options = self.available_parameters
        self._available_multi_parameters_select.options = self.available_multi_parameters
        self.sync_button_state()

    def sync_button_state(self, enabled: bool | None = None):
        if enabled is not None:
            self._enabled = enabled

        self._select_button.disabled = not (
            self._enabled and (self.max_selection > self.selection_size)
        )
        self._deselect_button.disabled = not self._enabled
        self._move_up_button.disabled = not self._enabled
        self._move_down_button.disabled = not self._enabled

    @property
    def layout(self) -> UIElement:
        return self._row


def _clear_other_on_selection(other):
    def clear_other(attr, old, new):
        if set(new) - set(old):
            other.value = []

    return clear_other
