from bokeh.io import curdoc

from qc_tool.app_state import AppState
from qc_tool.controllers.main_controller import MainController
from qc_tool.views.main_view import MainView


class QcTool:
    def __init__(self):
        app_state = AppState()
        main_controller = MainController(app_state)
        main_view = MainView(main_controller, app_state)
        curdoc().title = "QC Tool"
        curdoc().add_root(main_view.layout)


QcTool()
