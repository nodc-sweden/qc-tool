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
        Profile plots show median values (grey line) and 25 and 75 percentiles (grey area).
        Min and max values are shown in thin red lines.
        Statistics is based on data from 1993-2023 and is calculated per basin, month and standard depth.
        Basins outside 12 nm is according to HELCOM and OSPAR. Coastal data is aggregated per type.
    </div>

    <!-- Horizontal Line Separator -->
    <div style="grid-column: span 2;">
        <hr style="border: 1px solid #ccc; margin: 10px 0;">
    </div>

    <!-- Flag Descriptions -->
    <div>
        <p>Flag descriptions:</p>
       <ol>
            {% for flag_number, flag_name, color in qc_values %}
                {% if color != "gray" %}
                <li value="{{ flag_number }}">
                    <span style="color:{{ color }}; font-size: 1.5em;">●</span> {{ flag_name }}
                </li>
                {% endif %}
            {% endfor %}
        </ol>
        <p>
        <span style="color:black; font-size: 1.5em;">○</span> Flag changed by automatic or manual QC
        </p>
    </div>
    <div>
        <p>Order of tests performed in automatic QC:</p>
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
            qc_values=[
                (flag.value, str(flag), QC_FLAG_CSS_COLORS[flag]) for flag in QcFlag
            ],
            qc_colors=QC_FLAG_CSS_COLORS,
        )
        self._div = Div(text=flag_info_content)

    @property
    def layout(self):
        return self._div
