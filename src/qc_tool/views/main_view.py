from bokeh.models import Column, Row, TabPanel, Tabs

from qc_tool.app_state import AppState
from qc_tool.controllers.main_controller import MainController
from qc_tool.views.base_view import BaseView
from qc_tool.views.filter_view import FilterView
from qc_tool.views.help_view import HelpView
from qc_tool.views.summary_view import SummaryView
from qc_tool.views.visits_browser_view import VisitsBrowserView


class MainView(BaseView):
    def __init__(self, controller: MainController, state: AppState):
        self._controller = controller
        self._controller.main_view = self

        # Create child views
        self._filter_view = FilterView(self._controller.filter_controller, state.filter)

        self._visits_browser_view = VisitsBrowserView(
            self._controller.visits_browser_controller,
            state,
            self._controller.visits_browser_controller.map_controller,
            self._controller.visits_browser_controller.visit_selector_controller,
            self._controller.visits_browser_controller.profile_grid_controller,
            self._controller.visits_browser_controller.manual_qc_controller,
        )

        self._summary_view = SummaryView(
            self._controller.summary_controller,
            state,
            self._controller.summary_controller.map_controller,
            self._controller.summary_controller.file_controller,
            self._controller.summary_controller.validation_log_controller,
        )

        self._help_view = HelpView()

        # Create layout
        self._filter = Row(children=[self._filter_view.layout])
        self._tabs = Tabs(
            tabs=[
                TabPanel(child=self._summary_view.layout, title="Summary"),
                TabPanel(child=self._visits_browser_view.layout, title="Visits browser"),
                TabPanel(child=self._help_view.layout, title="Help"),
            ]
        )
        self._layout = Column(children=[self._filter, self._tabs])

    @property
    def layout(self):
        return self._layout
