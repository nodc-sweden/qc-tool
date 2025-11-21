import jinja2
from bokeh.models import Column, Div, ImportedStyleSheet, RadioButtonGroup, Row
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flag_tuple import QcField

from qc_tool.views.base_view import BaseView

_flag_info_template = jinja2.Template("""
{% if values %}
<h2>{{ values[0].name }}</h2>
<table>
    <thead>
        <tr>
            <th>QC Flag</th>
            <th>I</th>
            <th>A</th>
            <th>Depth</th>
            <th>Value</th>
        </tr>
    </thead>
    <tbody>
    {% for value in values %}
        <tr>
            <td><font color="{{ qc_colors[value.qc.total.value]}}">●</font> {{ value.qc.total }}</td>
            <td><font color="{{ qc_colors[value.qc.incoming.value]}}" title="{{ value.qc.incoming }}">●</font></td>
            <td>
                {% for flag in value.qc.automatic %}<font color="{{ qc_colors[flag.value]}}" title="{{ QcField(loop.index0).name }}: {{ flag }}">●</font>{% endfor %}
            </td>
            <td>{{value._data["DEPH"]}} m</td>
            <td>{{value._data["value"]}}</td>
        </tr>
    {% endfor %}
    </tbody>
</table>
{% endif %}
""")  # noqa: E501


class ManualQcHandler(BaseView):
    def __init__(self, values_changed_callback=None):
        self._manual_qc_header = Div(width=500, text="<h3>Perfom manual QC</h3>")
        self._manual_qc_info = Div(width=500, text="Select samples with the lasso tool")
        self._values = []
        self._values_changed_callback = values_changed_callback
        self._value_table = Div(
            text=_flag_info_template.render(values=[]),
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
        )
        self._qc_buttons = RadioButtonGroup(
            labels=[
                str(flag) for flag in QcFlag if not QC_FLAG_CSS_COLORS[flag] == "gray"
            ],
            orientation="vertical",
            active=None,
        )
        self._updating_qc_flag = False
        self._qc_buttons.on_change("active", self._qc_flag_changed)

        self._update()

    def select_values(self, values=None):
        values = values or []
        self._values = values
        self._update()

    def _update(self):
        qc_values = {value.qc.total for value in self._values}
        current_value = qc_values.pop() if len(qc_values) == 1 else None

        self._value_table.text = _flag_info_template.render(
            values=self._values, qc_colors=QC_FLAG_CSS_COLORS, QcField=QcField
        )
        self._qc_buttons.visible = bool(self._values)
        self._update_flag_button(current_value)

    def _update_flag_button(self, value):
        self._updating_qc_flag = True
        self._qc_buttons.active = value
        self._updating_qc_flag = False

    @property
    def layout(self):
        return Column(
            self._manual_qc_header,
            self._manual_qc_info,
            Row(self._value_table, self._qc_buttons),
        )

    def _qc_flag_changed(self, attr, old, new):
        if not self._updating_qc_flag:
            new_flag = QcFlag(new)
            for value in self._values:
                value.qc.manual = new_flag
            self._values_changed_callback(self._values)
