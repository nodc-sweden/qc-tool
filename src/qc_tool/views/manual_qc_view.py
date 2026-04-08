import typing

import jinja2
from bokeh.models import (
    Button,
    Column,
    Div,
    ImportedStyleSheet,
    MultiChoice,
    Row,
    Select,
    TextInput,
)
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS
from ocean_data_qc.fyskem.qc_flag_tuple import QcField

from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.views.base_view import BaseView

if typing.TYPE_CHECKING:
    from qc_tool.controllers.manual_qc_controller import ManualQcController
    from qc_tool.views.comment_dialog_view import CommentDialogView

_flag_info_template = jinja2.Template("""
<style>
  .deselect-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 1.6em; height: 1.6em; border-radius: 50%; cursor: pointer;
    border: 2px solid #c0bcbc; background: none; color: #c0bcbc;
    font-size: 1.3em; font-weight: bold; padding: 0; line-height: 1;
  }
  .deselect-btn:hover {
    border-color: #c0392b; color: #c0392b;
  }
</style>
<table>
    <thead>
        <tr>
            <th></th>
            <th>Depth</th>
            <th>Parameter</th>
            <th>Value</th>
            <th>QC Flag</th>
            <th>I</th>
            <th>A</th>
            <th>Category</th>
            <th>Comment</th>
        </tr>
    </thead>
    <tbody>
    {% for value in values %}
        <tr>
            <td>
              <button class="deselect-btn"
                onclick="Bokeh.documents[0].get_model_by_id(
                  '{{ deselect_model_id }}'
                ).value = '{{ loop.index0 }}'">x</button>
            </td>
            <td>{{value._data["DEPH"]}} m</td>
            <td>{{value.name}}</td>
            <td>{{value._data["value"]}}</td>
            <td>
              <font color="{{ qc_colors[value.qc.total] }}">●</font> {{ value.qc.total }}
            </td>
            <td>
              <font color="{{ qc_colors[value.qc.incoming] }}"
                    title="{{ value.qc.incoming }}">●</font>
            </td>
            <td>
            {% for flag in value.qc.automatic %}
              <font color="{{ qc_colors[flag] }}"
                    title="{{ QcField(loop.index0).name }}: {{ flag }}">●</font>
            {% endfor %}
            </td>
            <td>{{value.manual_category}}</td>
            <td>{{value.manual_comment}}</td>
        </tr>
    {% endfor %}
    </tbody>
</table>
""")


class ManualQcView(BaseView):
    def __init__(
        self,
        controller: "ManualQcController",
        manual_qc_model: ManualQcModel,
    ):
        self._controller = controller
        self._controller.manual_qc_view = self

        self._manual_qc_model = manual_qc_model
        self._manual_qc_model.register_listener(
            ManualQcModel.VALUES_SELECTED, self._on_values_selected
        )
        self._manual_qc_model.register_listener(
            ManualQcModel.FLAG_CANCELLED, self._on_flag_cancelled
        )
        self._manual_qc_model.register_listener(ManualQcModel.QC_PERFORMED, self._update)

        self.comment_dialog_view: "CommentDialogView | None" = None

        common_config = {
            "min_width": 200,
        }
        self._manual_qc_header = Div(
            text="<h3>Manual QC</h3><p>Set manual flags on the selected values below.</p>"
        )

        self._parameter_selector = MultiChoice(title="Parameters", **common_config)
        self._range_min_selector = Select(
            title="Min depth", options=["-"], value="-", width=50
        )
        self._range_max_selector = Select(
            title="Max depth", options=["-"], value="-", width=50
        )
        self._depth_selector = MultiChoice(title="Depths", **common_config)
        self._set_flag_button = Button(label="Set flag", styles={"height": "100%"})
        self._select_row = Column(
            Row(
                self._parameter_selector,
                self._range_min_selector,
                self._range_max_selector,
                self._depth_selector,
            ),
            self._set_flag_button,
        )

        self._deselect_trigger = TextInput(value="-1", visible=False)
        self._deselect_trigger.on_change("value", self._on_deselect_triggered)

        self._value_table = Div(
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
            styles={"max-height": "400px", "overflow-y": "auto"},
        )

        self._depth_selector.on_change("value", self._on_depths_changed)
        self._range_min_selector.on_change("value", self._on_range_changed)
        self._range_max_selector.on_change("value", self._on_range_changed)
        self._parameter_selector.on_change("value", self._on_parameters_changed)
        self._set_flag_button.on_click(self._on_flag_button_clicked)
        self._update()

    def _on_parameters_changed(self, _attr, _old, _new):
        self._controller.on_filter_changed(
            self._depth_selector.value,
            self._parameter_selector.value,
        )

    def _on_depths_changed(self, _attr, _old, _new):
        for selector in (self._range_min_selector, self._range_max_selector):
            selector.remove_on_change("value", self._on_range_changed)
            selector.value = "-"
            selector.on_change("value", self._on_range_changed)
        self._controller.on_filter_changed(
            self._depth_selector.value, self._parameter_selector.value
        )

    def _on_range_changed(self, _attr, _old, _new):
        depths = self._depths_in_range()
        self._depth_selector.remove_on_change("value", self._on_depths_changed)
        self._depth_selector.value = depths
        self._depth_selector.on_change("value", self._on_depths_changed)
        self._controller.on_filter_changed(depths, self._parameter_selector.value)

    def _depths_in_range(self) -> list[str]:
        min_str = self._range_min_selector.value
        max_str = self._range_max_selector.value
        if min_str == "-" and max_str == "-":
            return []
        depths = self._depth_selector.options
        if min_str != "-":
            depths = [d for d in depths if float(d) >= float(min_str)]
        if max_str != "-":
            depths = [d for d in depths if float(d) <= float(max_str)]
        return depths

    def _on_deselect_triggered(self, _attr, _old, new):
        try:
            index = int(new)
            if index >= 0:
                self._controller.deselect_value(index)
                self._deselect_trigger.value = "-1"
        except ValueError:
            pass

    def _on_values_selected(self):
        self._update()

    def _on_flag_cancelled(self):
        self._update()

    def _update(self):
        self._value_table.text = _flag_info_template.render(
            values=self._manual_qc_model.selected_values,
            deselect_model_id=self._deselect_trigger.id,
            qc_colors=QC_FLAG_CSS_COLORS,
            QcField=QcField,
        )

    @property
    def layout(self):
        return Column(
            self._manual_qc_header,
            self._select_row,
            self._deselect_trigger,
            self._value_table,
            self.comment_dialog_view.layout,
        )

    def update_depths(self, depths: list[str]):
        range_options = ["-", *map(str, range(0, int(max(map(float, depths))), 5))]
        for selector in (self._range_min_selector, self._range_max_selector):
            selector.remove_on_change("value", self._on_range_changed)
            selector.options = range_options
            selector.value = "-"
            selector.on_change("value", self._on_range_changed)
        self._depth_selector.options = depths
        self._depth_selector.value = [
            v for v in self._depth_selector.value if v in depths
        ]

    def update_parameters(self, parameters: list[str]):
        self._parameter_selector.options = parameters
        self._parameter_selector.value = [
            value for value in self._parameter_selector.value if value in parameters
        ]

    def _on_flag_button_clicked(self, _event):
        self._controller.set_flag()
