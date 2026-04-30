import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.visit_info_controller import VisitInfoController

import jinja2
from bokeh.models import DataTable, Div, ImportedStyleSheet

from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.base_view import BaseView

# check_ok.png The Oxygen Team, KDE;, LGPL <https://www.gnu.org/copyleft/lgpl.html>,
# via Wikimedia Commons

_full_template = jinja2.Template("""
<div class="visit-info-container">

    <div class="metadata-section">
        <table>
            {% for key, value in metadata %}
            <tr>
                <th>{{ key }}</th>
                <td class="metadata-value">{{ value }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="log-section">

        <div class="collapsible-container">

            <!-- Hidden checkbox toggle -->
            <input type="checkbox" id="toggle-log" class="toggle">

            <!-- Clickable label -->
            <label for="toggle-log" class="toggle-label">

                {% if logs %}
                    <img src="/qc_tool/static/images/warning.svg"
                         style="height:20px; vertical-align:middle; margin-right:8px;">
                    ({{ logs|length }})
                {% else %}
                    <img src="/qc_tool/static/images/check_ok.png"
                         style="height:20px; vertical-align:middle; margin-right:8px;">
                    (0)
                {% endif %}

            </label>

            <!-- Collapsible content-->
            <div class="collapsible-content">
                <div class="content-inner">

                    {% if logs %}
                        <ul>
                        {% for log in logs %}
                            <li class="log-{{ log.level }}">
                                <strong>{{ log.level }}:</strong>
                                {{ log.msg }}
                            </li>
                        {% endfor %}
                        </ul>
                    {% else %}
                        <p>No validation messages</p>
                    {% endif %}

                </div>
            </div>

        </div>

    </div>

</div>
""")


class VisitInfoView(BaseView):
    def __init__(
        self, controller: "VisitInfoController", visit_model: VisitsModel, width=600
    ):
        self._controller = controller
        controller.visit_info_view = self

        self._visits_model = visit_model
        self._table = DataTable(width=width)
        self._div = Div(
            width=width,
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
        )

    def update(self, metadata: list, logs: list[dict]):
        self._div.text = _full_template.render(metadata=metadata, logs=logs)

    @property
    def layout(self):
        return self._div
