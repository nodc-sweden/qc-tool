import typing

if typing.TYPE_CHECKING:
    from qc_tool.controllers.file_controller import FileController

import tkinter.filedialog
from pathlib import Path

from bokeh.io import curdoc
from bokeh.models import (
    Button,
    Column,
    Div,
    FileInput,
    ImportedStyleSheet,
    Row,
    TablerIcon,
)

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
        self._select_data_button = Button(
            label="Select data...",
            icon=TablerIcon(icon_name="file-import", size="1.2em"),
            styles={"margin-top": "20px"},
        )
        self._select_data_button.on_click(self._on_select_data_button_clicked)

        self._save_working_file_button = Button(
            label="Save working file...",
            icon=TablerIcon(icon_name="device-floppy", size="1.2em"),
            disabled=True,
        )
        self._save_working_file_button.on_click(self._on_save_working_file_button_clicked)

        self._load_working_file_button = Button(
            label="Load working file...",
            icon=TablerIcon(icon_name="folder-open", size="1.2em"),
            disabled=True,
        )
        self._load_working_file_button.on_click(self._on_load_working_file_button_clicked)

        self._working_state_section = Column(
            Div(text="<i>Save or load you current working state:</i>"),
            Row(self._save_working_file_button, self._load_working_file_button),
            styles={
                "border": "1px solid #ccc",
                "padding": "5px",
                "border-radius": "4px",
                "margin-top": "20px",
            },
        )

        self._export_feedback_file_button = Button(
            label="Export feedback file...",
            icon=TablerIcon(icon_name="file-export", size="1.2em"),
            disabled=True,
            styles={"margin-top": "20px"},
        )
        self._export_feedback_file_button.on_click(
            self._on_export_feedback_button_clicked
        )

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
            self._select_data_button,
            self._working_state_section,
            self._export_feedback_file_button,
        )

    def _on_save_working_file_button_clicked(self, event):
        try:
            root = tkinter.Tk()
            root.iconify()
            selected_path = tkinter.filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            )
            root.destroy()
        except tkinter.TclError:
            selected_path = None

        if not selected_path:
            return
        selected_path = Path(selected_path)
        self._controller.save_data(selected_path)

    def _on_select_data_button_clicked(self, event):
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

    def _on_load_working_file_button_clicked(self, event):
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
        curdoc().add_next_tick_callback(
            lambda: self._controller.load_working_file(
                selected_path, self._file_model.data
            )
        )

    def _on_export_feedback_button_clicked(self, event):
        try:
            root = tkinter.Tk()
            root.iconify()
            selected_path = tkinter.filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
            )
            root.destroy()
        except tkinter.TclError:
            selected_path = None

        if not selected_path:
            return
        selected_path = Path(selected_path)
        self._controller.save_changed_data(selected_path)

    @property
    def layout(self):
        return self._layout

    def file_load_completed(self):
        self._load_indicator.visible = False
        self._load_working_file_button.disabled = self._file_model.data is None
        self._save_working_file_button.disabled = self._file_model.data is None
        self._export_feedback_file_button.disabled = self._file_model.data is None

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

    def feedback_load_completed(self):
        self._load_indicator.visible = False
