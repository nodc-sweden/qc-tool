import typing

from qc_tool.data_transformation import shortest_unique_paths
from qc_tool.models.ctd_file_model import CtdFileModel

if typing.TYPE_CHECKING:
    from qc_tool.controllers.file_controller import FileController

import tkinter.filedialog
from pathlib import Path

from bokeh.io import curdoc
from bokeh.models import (
    Button,
    Column,
    Dialog,
    Div,
    FileInput,
    ImportedStyleSheet,
    Row,
    Switch,
    TablerIcon,
)

from qc_tool.models.file_model import FileModel
from qc_tool.views.base_view import BaseView


class FileView(BaseView):
    def __init__(
        self,
        controller: "FileController",
        file_model: FileModel,
        ctd_file_model: CtdFileModel,
    ):
        self._controller = controller
        self._controller.file_view = self

        self._file_model = file_model
        self._ctd_file_model = ctd_file_model

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
        )
        self._select_data_button.on_click(self._on_select_data_button_clicked)

        self._add_to_existing = Switch(label="Add to loaded data", active=False)
        self._load_data_section = Column(
            self._select_data_button, self._add_to_existing, styles={"margin-top": "20px"}
        )

        self._select_ctd_data_button = Button(
            label="Select CTD data...",
            icon=TablerIcon(icon_name="file-import", size="1.2em"),
            disabled=True,
        )
        self._select_ctd_data_button.on_click(self._on_select_ctd_data_button_clicked)
        self._load_ctd_file_section = Column(
            self._select_ctd_data_button, styles={"margin-top": "20px"}
        )

        self._load_file_section = Row(
            self._load_data_section, self._load_ctd_file_section
        )

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

        self._save_file_buttons = Column()
        self._save_selection_dialog = Dialog(
            title="Save working file",
            content=self._save_file_buttons,
            visible=False,
            closable=True,
            minimizable=False,
            maximizable=False,
            collapsible=False,
            pinnable=False,
            styles={"width": "fit-content", "height": "fit-content"},
        )

        self._layout = Column(
            self._load_header,
            self._loaded_file_label,
            self._load_indicator,
            self._load_file_section,
            self._working_state_section,
            self._export_feedback_file_button,
            self._save_selection_dialog,
        )

    def _on_save_working_file_button_clicked(self, event):
        if len(self._file_model.file_paths) > 1:
            self._save_selection_dialog.visible = True
            return
        self._save_file(self._file_model.file_paths[0])

    def _save_file(self, source_path: Path):
        self._save_selection_dialog.visible = False
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
        self._controller.save_data_for_source(source_path, Path(selected_path))

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
        self._loaded_file_label.text = "Loading data..."
        curdoc().add_next_tick_callback(
            lambda: self._controller.load_file(
                selected_path, self._add_to_existing.active
            )
        )

    def _on_select_ctd_data_button_clicked(self, event):
        try:
            root = tkinter.Tk()
            root.iconify()
            selected_path = tkinter.filedialog.askdirectory()
            root.destroy()
        except tkinter.TclError:
            selected_path = None

        if not selected_path:
            return

        selected_path = Path(selected_path)
        self._load_indicator.visible = True
        self._loaded_file_label.text = "Loading CTD data..."
        curdoc().add_next_tick_callback(
            lambda: self._controller.load_ctd_file(selected_path)
        )

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
        self._loaded_file_label.text = "Loading working file..."
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
        self._update_file_list()

        no_data = self._file_model.data is None
        self._select_ctd_data_button.disabled = no_data
        self._load_working_file_button.disabled = no_data
        self._save_working_file_button.disabled = no_data
        self._export_feedback_file_button.disabled = no_data

        file_paths = self._file_model.file_paths
        short_names = shortest_unique_paths(file_paths)

        buttons = []
        for path in file_paths:
            button = Button(
                label=short_names[path],
                icon=TablerIcon(icon_name="device-floppy", size="1.2em"),
            )
            button.on_click(lambda event, p=path: self._save_file(p))
            buttons.append(button)
        self._save_file_buttons.children = buttons

    def feedback_load_completed(self):
        self._load_indicator.visible = False
        self._update_file_list()

    def ctd_load_completed(self):
        self._load_indicator.visible = False
        self._update_file_list()

    def _update_file_list(self):
        file_paths = self._file_model.file_paths + self._ctd_file_model.file_paths
        short_names = shortest_unique_paths(file_paths)

        if self._file_model.file_paths:
            lines = "\n".join(
                f"<span style='font-style: italic; display: block; line-height: 1.2;'"
                f" onmouseover=\"this.style.background='#e0e0e0'\""
                f" onmouseout=\"this.style.background=''\""
                f" title='{path}'>{short_names[path]}</span>"
                for path in self._file_model.file_paths
            )
            file_info = f"<label>Files:</label>{lines}"

            if self._ctd_file_model.file_paths:
                ctd_lines = "\n".join(
                    f"<span style='font-style: italic; display: block; line-height: 1.2;'"
                    f" onmouseover=\"this.style.background='#e0e0e0'\""
                    f" onmouseout=\"this.style.background=''\""
                    f" title='{path}'>{short_names[path]}</span>"
                    for path in self._ctd_file_model.file_paths
                )
                file_info += f"<br /><label>CTD files:</label>{ctd_lines}"
        else:
            file_info = (
                "<label>File:</label><p style='font-style: italic;'>No file loaded</p>"
            )
        self._loaded_file_label.text = file_info
