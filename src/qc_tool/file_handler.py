import tkinter
import tkinter.filedialog
from pathlib import Path

import pandas as pd
import sharkadm
import sharkadm.data
from bokeh.models import Button, Column, Div, FileInput

from qc_tool.protocols import Layoutable


class FileHandler(Layoutable):
    def __init__(self, external_load_file_callback):
        self._file_name = None
        self._external_load_file_callback = external_load_file_callback
        self._div = Div(width=500)
        self._file_input = FileInput(
            title="Select file:", accept=".txt,.csv", max_width=500
        )
        self._file_button = Button(label="Select data...")
        self._file_button.on_click(self._internal_load_file_callback)
        self._update_info()

    def _internal_load_file_callback(self, event):
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

        lims_directory = sharkadm.data.lims.directory_is_lims(selected_path)
        if lims_directory:
            self._file_name = lims_directory.name
            self._update_info()
            data = sharkadm.lims_data.get_row_data_from_lims_export(lims_directory)
        else:
            self._file_name = selected_path.name
            self._update_info()
            data = pd.read_csv(selected_path, sep="\t")

        self._external_load_file_callback(data)

    def _update_info(self):
        if self._file_name:
            file_info = f"<h3>{self._file_name}</h3>"
        else:
            file_info = "<h3>No file loaded</h3>"
        self._div.text = file_info

    @property
    def layout(self):
        return Column(self._file_button, self._div)
