import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.visits_controller import SummaryController

from bokeh.models import Column, Row, Tabs
from bokeh.models.layouts import TabPanel

from qc_tool.app_state import AppState
from qc_tool.views.base_view import BaseView
from qc_tool.views.file_view import FileView
from qc_tool.views.map_view import MapView
from qc_tool.views.validation_log_view import ValidationLogView


class SummaryView(BaseView):
    def __init__(
        self,
        controller: "SummaryController",
        state: AppState,
        map_controller,
        file_controller,
        validation_log_controller,
    ):
        self._controller = controller
        self._controller.summary_view = self

        self.map_view = MapView(map_controller, state.map)

        self.file_view = FileView(file_controller, state.file)
        file_controller.file_view = self.file_view

        self._validation_view = ValidationLogView(
            validation_log_controller, state.validation_log
        )

        self._main_info = Row(
            children=[
                self.map_view.layout,
                self.file_view.layout,
            ]
        )

        self._info_tabs = Tabs(
            tabs=[TabPanel(title="Validation log", child=self._validation_view.layout)]
        )

        self._layout = Column(
            children=[
                self._main_info,
                self._info_tabs,
            ]
        )

    def update_validation_log(self, validation):
        self._validation_view.update(validation)

    @property
    def layout(self):
        return self._layout
