import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.visits_browser_controller import VisitsBrowserController

from pathlib import Path

import jinja2
from bokeh.models.layouts import Column, Row, TabPanel, Tabs

from qc_tool.app_state import AppState
from qc_tool.data_transformation import changes_report
from qc_tool.scatter_slot import ScatterSlot
from qc_tool.views.base_view import BaseView
from qc_tool.views.manual_qc_view import ManualQcView
from qc_tool.views.map_view import MapView
from qc_tool.views.parameter_selector_view import ParameterSelectorView
from qc_tool.views.profile_grid_view import ProfileGridView
from qc_tool.views.visit_info_view import VisitInfoView
from qc_tool.views.visit_selector_view import VisitSelectorView

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

physical_parameters = (
    "SALT_CTD",
    "SALT_BTL",
    "TEMP_CTD",
    "TEMP_BTL",
    "DOXY_CTD",
    "DOXY_BTL",
    "H2S",
    "CHLFL",
)

chemical_parameters = (
    "SIO3-SI",
    "PHOS",
    "PTOT",
    "NTOT",
    "AMON",
    "NTRI",
    "NTRA",
    "NTRZ",
)

biological_parameters = ("CPHL", "CHLFL", "PH_LAB", "PH_TOT", "ALKY", "HUMUS")


class VisitsBrowserView(BaseView):
    def __init__(
        self,
        controller: "VisitsBrowserController",
        state: AppState,
        map_controller,
        visit_selector_controller,
        profile_grid_controller,
        manual_qc_controller,
    ):
        self._controller = controller
        self._controller.visits_browser_view = self

        self._state = state

        self._map_view = MapView(map_controller, state.map, 400, 300)
        self._visit_selector_view = VisitSelectorView(
            visit_selector_controller, state.visits, state.filter
        )

        self._station_info = VisitInfoView(
            controller.visit_info_controller, state.visits, width=400
        )

        self._manual_qc_view = ManualQcView(manual_qc_controller, self._state.manual_qc)

        self._scatter_parameters = [
            ScatterSlot(
                self._state.visits, x_parameter="DOXY_BTL", y_parameter="DOXY_CTD"
            ),
            ScatterSlot(self._state.visits, x_parameter="ALKY", y_parameter="SALT_CTD"),
            ScatterSlot(self._state.visits, x_parameter="PHOS", y_parameter="NTRZ"),
            ScatterSlot(self._state.visits, x_parameter="NTRZ", y_parameter="H2S"),
        ]

        # Top row
        navigation_column = Column(
            self._visit_selector_view.layout,
            self._map_view.layout,
            sizing_mode="stretch_both",
            width=400,
        )

        self._parameter_handler = ParameterSelectorView(
            self._controller.parameter_selector_controller,
            self._state.parameters,
            self._state.profile_grid,
        )

        top_row = Row(
            navigation_column,
            self._station_info.layout,
            self._parameter_handler.layout,
            self._manual_qc_view.layout,
            sizing_mode="stretch_width",
        )

        self._profile_tab_handler = ProfileGridView(
            profile_grid_controller,
            state.profile_grid,
            state.parameters,
            state.visits,
            state.manual_qc,
        )

        self._profile_tab = TabPanel(
            child=self._profile_tab_handler.layout,
            title="Profiles",
        )

        # Tab for scatter plots
        scatter_tab = TabPanel(
            child=Row(
                children=[parameter.layout for parameter in self._scatter_parameters]
            ),
            title="Scatter",
        )

        bottom_row = Tabs(tabs=[self._profile_tab, scatter_tab])

        # Full layout
        self._layout = Column(top_row, bottom_row)

    def save_file_callback(self, filename: Path):
        self._data.write_csv(filename, separator="\t")

    def save_diff_file_callback(self, filename: Path):
        changes_report(self._data).write_excel(
            filename,
            header_format={"bold": True, "border": 2},
            freeze_panes=(1, 0),
        )

    def parameter_handler_callback(self, *, columns, rows):
        self._profile_tab_handler.sync_profiles(columns=columns, rows=rows)
        self._profile_tab.child = self._profile_tab_handler.layout

    def _set_extra_info_tab(self, index: int):
        self._extra_info_tabs.active = index

    def _set_validation(self, validation: dict):
        self._validation = validation
        self._log_div.text = _validation_log_template.render(validation=validation)

    @property
    def layout(self):
        return self._layout

    def update_scatter_plots(self):
        for plot in self._scatter_parameters:
            plot.update_station()
