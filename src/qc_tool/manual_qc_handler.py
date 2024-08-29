import jinja2
from bokeh.models import Div, RadioButtonGroup, Column, Row
from ocean_data_qc.fyskem.qc_flag import QcFlag, QC_FLAG_CSS_COLORS

from qc_tool.protocols import Layoutable

_flag_info_template = jinja2.Template("""
<p>Points:</p>
<ul start=0>
    {% for value in values %}<li>
        <font color="{{ qc_colors[value["manual_qc"]] }}">●</font> {{ value["depth"] }}: {{value["value"]}}
    </li>{% endfor %}
</ul>
""")

class ManualQcHandler(Layoutable):
    def __init__(self):
        values =
        self._något_annat = Div(text=_flag_info_template.render(values=values, qc_colors=QC_FLAG_CSS_COLORS))
        self._qc_buttons = RadioButtonGroup(labels=[flag.name.replace("_", " ").title() for flag in QcFlag], orientation="vertical")

    @property
    def layout(self):
        return Column(self._div, Row(self._qc_buttons))

