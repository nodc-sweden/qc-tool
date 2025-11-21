import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.file_controller import FileController

import tkinter
from pathlib import Path

from bokeh.io import curdoc
from bokeh.models import Button, Column, Div, FileInput, ImportedStyleSheet

from qc_tool.controllers.file_controller import FileController
from qc_tool.models.file_model import FileModel
from qc_tool.views.base_view import BaseView


class FileView(BaseView):
    def __init__(self, controller: "FileController", file_model: FileModel):
        self._controller = controller
        self._controller.file_view = self

        self._file_model = file_model

        self._load_header = Div(width=500, text="<h3>Load and save</h3>")
        self._loaded_file_label = Div(
            width=500,
            text="<label>File:</label><p style='font-style: italic;'>No file loaded</p>",
        )
        self._file_input = FileInput(
            title="Select file:", accept=".txt,.csv", max_width=500
        )
        self._load_button = Button(label="Select data...")
        self._load_button.on_click(self._load_button_clicked)
        self._save_as_button = Button(label="Save as...")
        self._save_as_button.on_click(self._save_button_clicked)
        self._save_changes_as_button = Button(label="Save only changed rows as...")
        self._save_changes_as_button.on_click(self._save_changes_clicked)

        self._load_indicator = Div(
            width=50,
            height=50,
            text='<div class="loader"></div>',
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
            visible=False,
        )

        self._layout = Column(
            self._load_header,
            self._loaded_file_label,
            self._load_indicator,
            self._load_button,
            self._save_as_button,
            self._save_changes_as_button,
        )

    def _save_button_clicked(self, event):
        pass

    def _load_button_clicked(self, event):
        try:
            root = tkinter.Tk()
            root.iconify()
            selected_path = tkinter.filedialog.askopenfilename()
            root.destroy()
        except tkinter.TclError:
            selected_path = None

        if not selected_path:
            return
        selected_path = Path(selected_path)
        self._load_indicator.visible = True
        self._loaded_file_label.text = "Loading..."
        curdoc().add_next_tick_callback(lambda: self._controller.load_file(selected_path))

    def _save_changes_clicked(self, event):
        pass

    @property
    def layout(self):
        return self._layout

    def _file_load_completed(self):
        self._load_indicator.visible = False
        if self._file_model.file_path:
            file_info = (
                f"<label>File:</label>"
                f"<p style='font-style: italic;'>{self._file_model.file_path}</p>"
            )
        else:
            file_info = (
                "<label>File:</label><p style='font-style: italic;'>No file loaded</p>"
            )
        self._loaded_file_label.text = file_info
