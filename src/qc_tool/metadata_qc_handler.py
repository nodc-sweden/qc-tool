import jinja2
from bokeh.models import Column, Div, ImportedStyleSheet

from qc_tool.layoutable import Layoutable
from qc_tool.station import Station

_log_template = jinja2.Template("""
{% if qc_log %}
{% for category, fields in qc_log.items() %}
<h3>{{ category.name }} check</h3>
{% for field, messages in fields.items() %}
<h4>{{ field }}:</h4>
<ul>
{% for message in messages %}
    <li>{{ message }}</li>
{% endfor %}
</ul>
{% endfor %}
{% endfor %}
{% endif %}
""")  # noqa: E501


class MetadataQcHandler(Layoutable):
    def __init__(self):
        self._station = None
        self._manual_qc_header = Div(width=500, text="<h3>Results of metadata QC</h3>")
        self._log_table = Div(
            text=_log_template.render(values=[]),
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
        )
        self.update()

    def set_station(self, station: Station):
        self._station = station
        self.update()

    def update(self):
        if self._station and self._station._visit.qc_log:
            self._log_table.text = _log_template.render(
                qc_log=self._station._visit.qc_log
            )
        else:
            self._log_table.text = _log_template.render(qc_log=None)

    @property
    def layout(self):
        return Column(self._manual_qc_header, self._log_table)
