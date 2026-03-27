import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.validation_log_controller import ValidationLogController

import jinja2
from bokeh.models import Div, ImportedStyleSheet

from qc_tool.models.validation_log_model import ValidationLogModel
from qc_tool.views.base_view import BaseView

_validation_log_template = jinja2.Template("""
{% for key, value in validation.items() %}
  {% if value.count > 0 %}
  <div class="collapsible-container">
    <input id="collapsible-{{ key }}" class="toggle" type="checkbox">
    <label for="collapsible-{{ key }}" class="toggle-label">
      {{ key }} ({{ value.count }} messages)
    </label>
    <div class="collapsible-content">
      <div class="content-inner">
        <p>{{ value.description }}</p>
        <ul>
        {% for category, messages in value.messages.items() %}
          {% if category != "General" %}
            <li><strong>{{ category }}</strong></li>
            <ul>
          {% endif %}

          {% for msg in messages %}
              <li>{{ msg }}</li>
          {% endfor %}

          {% if category != "General" %}
            </ul>
          {% endif %}
        {% endfor %}
        </ul>
      </div>
    </div>
  </div>
  {% endif %}
{% endfor %}
""")


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

    def update(self, validation_remarks):
        self._layout.text = _validation_log_template.render(validation=validation_remarks)

    @property
    def layout(self):
        return self._layout
