import jinja2
from bokeh.models import Div
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flag_tuple import QcField

from qc_tool.layoutable import Layoutable

_flag_info_template = jinja2.Template("""
<div style="display: grid; grid-template-columns: 1fr 1fr; max-width: 600px;">
    <!-- Header Row -->
    <div style="font-weight: bold; font-size: 16px; padding-bottom: 5px;">
        INFORMATION
    </div>
    <div></div>  <!-- Empty div to maintain grid structure -->

    <!-- Information Text -->
    <div style="grid-column: span 2; font-size: 14px; margin-bottom: 10px;">
        Profile plots show median values and 25 and 75 percentiles.\n
        Min and max values are shown in thin red lines.
        Statistics is based on data from 1993-2023 and is calculated per basin, month and standard depth\n
        Basins outside 12 nm is according to HELCOM and OSPAR. Coastal data is aggregated per type.
    </div>

    <!-- Horizontal Line Separator -->
    <div style="grid-column: span 2;">
        <hr style="border: 1px solid #ccc; margin: 10px 0;">
    </div>

    <!-- Flag Descriptions -->
    <div>
        <p>Flag descriptions:</p>
        <ol start=0>
            {% for qc_value in qc_values %}<li>
                <font color="{{ qc_colors[qc_value] }}">●</font> {{ qc_value }}
            </li>{% endfor %}
        </ol>
        <p><span style="color:black;">○</span> Flag changed by automatic or manual qc</p>
    </div>
    <div>
        <p>Tests performed in automatic QC:</p>
        <ol>
            {% for qc_field in qc_fields %}<li>{{ qc_field }}</li>{% endfor %}
        </ol>
    </div>
</div>
""")  # noqa: E501


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
