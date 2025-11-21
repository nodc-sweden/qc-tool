import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.visit_info_controller import VisitInfoController

import jinja2
from bokeh.models import DataTable, Div, ImportedStyleSheet

from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.base_view import BaseView

_metadata_template = jinja2.Template("""
<table>
    {% for key, value, class in metadata %}
    <tr class="{{ class }}">
        <th>{{ key }}</th>
        <td class="metadata-value">{{ value }}</td>
        <td class="metadata-status"></td>
    </tr>
    {% endfor %}
</table>
""")


class VisitInfoView(BaseView):
    def __init__(
        self, controller: "VisitInfoController", visit_model: VisitsModel, width=400
    ):
        self._controller = controller
        controller.visit_info_view = self

        self._visits_model = visit_model
        self._table = DataTable(width=width)
        self._div = Div(
            width=width,
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
        )

    def update(self, metadata: list):
        self._div.text = _metadata_template.render(metadata=metadata)

    @property
    def layout(self):
        return self._div
