import jinja2
from bokeh.models import Div
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flag_tuple import QcField

from qc_tool.layoutable import Layoutable

_flag_info_template = jinja2.Template("""
<div style="display: grid; grid-template-columns: 1fr 1fr">
    <div>
        <p>QC values:</p>
        <ol start=0>
            {% for qc_value in qc_values %}<li>
                <font color="{{ qc_colors[qc_value] }}">●</font> {{ qc_value }}
            </li>{% endfor %}
        </ol>
    </div>
    <div>
        <p>Automatic QC fields:</p>
        <ol>
            {% for qc_field in qc_fields %}<li>{{ qc_field }}</li>{% endfor %}
        </ol>
    </div>
</div>
""")


class FlagInfo(Layoutable):
    def __init__(self):
        flag_info_content = _flag_info_template.render(
            qc_fields=[value.name for value in QcField],
            qc_values=QcFlag,
            qc_colors=QC_FLAG_CSS_COLORS,
        )
        self._div = Div(text=flag_info_content)

    @property
    def layout(self):
        return self._div
