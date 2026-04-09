import argparse
import sys
from pathlib import Path

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

        startup_file = self._parse_startup_file()
        if startup_file:
            file_controller = main_controller.summary_controller.file_controller
            curdoc().add_next_tick_callback(
                lambda: file_controller.load_file(startup_file)
            )

    @staticmethod
    def _parse_startup_file():
        parser = argparse.ArgumentParser()
        parser.add_argument("--file", type=Path)
        args, _ = parser.parse_known_args(sys.argv[1:])
        return args.file


QcTool()
