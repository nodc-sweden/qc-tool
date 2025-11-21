import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.validation_log_controller import ValidationLogController

import jinja2
from bokeh.models import Div, ImportedStyleSheet

from qc_tool.models.validation_log_model import ValidationLogModel
from qc_tool.views.base_view import BaseView

_validation_log_template = jinja2.Template("""
{% for key, value in validation.items() %}
  <div class="collapsible-container">
    <input id="collapsible-{{ key }}" class="toggle" type="checkbox">
    <label for="collapsible-{{ key }}" class="toggle-label{% if value.fail_count %} errors{% endif %}">{{ key }} ({{ value.success_count }} successes, {{ value.fail_count }} errors)</label>
    <div class="collapsible-content">
      <div class="content-inner">
      {% if value.fail %}
        <p>{{ value.description }}</p>
        <ul>
        {% for category, fail_rows in value.fail.items() %}
          {% if category != "General" %}
          <li>{{ category }}</li>
            <ul>
          {% endif %}
          {% for fail_row in fail_rows %}
              <li>{{ fail_row }}</li>
          {% endfor %}
          {% if category != "General" %}
            </ul>
          {% endif %}
        {% endfor %}
        </ul>
      {% else %}
        <p>No validation errors.</p>
      {% endif %}
      </div>
    </div>
  </div>
{% endfor %}
""")  # noqa: E501


class ValidationLogView(BaseView):
    def __init__(
        self,
        controller: "ValidationLogController",
        validation_log_model: ValidationLogModel,
    ):
        self._controller = controller
        self._controller.validation_log_view = self

        self._validation_log_model = validation_log_model

        self._layout = Div(
            width=1000,
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
        )

    def update(self, validation_log):
        self._layout.text = _validation_log_template.render(validation=validation_log)

    @property
    def layout(self):
        return self._layout
