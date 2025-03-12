import tkinter
import tkinter.filedialog
from pathlib import Path

import sharkadm
from bokeh.models import Button, Column, Div, FileInput
from sharkadm import exporters, transformers

from qc_tool.layoutable import Layoutable


class FileHandler(Layoutable):
    def __init__(
        self,
        external_load_file_callback,
        external_save_file_callback,
        external_save_changes_file_callback,
        external_automatic_qc_callback,
    ):
        self._file_name = None

        self._external_load_file_callback = external_load_file_callback
        self._external_save_file_callback = external_save_file_callback
        self._external_save_changes_file_callback = external_save_changes_file_callback
        self._external_automatic_qc_callback = external_automatic_qc_callback

        self._load_header = Div(width=500, text="<h3>Load and save</h3>")
        self._loaded_file_label = Div(width=500)
        self._file_input = FileInput(
            title="Select file:", accept=".txt,.csv", max_width=500
        )

        self._file_button = Button(label="Select data...")
        self._file_button.on_click(self._load_file_callback)

        self._save_as_button = Button(label="Save as...")
        self._save_as_button.on_click(
            lambda: self._save_file_as_callback(self._external_save_file_callback)
        )

        self._save_changes_as_button = Button(label="Save only changed rows as...")
        self._save_changes_as_button.on_click(
            lambda: self._save_file_as_callback(self._external_save_changes_file_callback)
        )

        self._qc_header = Div(width=500, text="<h3>QC</h3>")

        self._qc_button = Button(label="Automatic QC...")
        self._qc_button.on_click(self._automatic_qc_callback)
        self._qc_button.disabled = True

        self._file_loaded()

    def _load_file_callback(self, event):
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
        print(f"load data from {selected_path}...")
        controller = sharkadm.get_controller_with_data(selected_path)
        self._apply_transformers(controller=controller)
        print("data loaded")
        data = controller.export(
            exporters.DataFrame(header_as="PhysicalChemical", float_columns=True)
        )
        self._file_name = selected_path.name
        self._file_loaded()
        self._external_load_file_callback(data)

    def _apply_transformers(self, controller):
        # this is already be handled in get_controller_with_data
        # controller.set_data_holder(data_holder)
        controller.transform(transformers.AddRowNumber())
        controller.transform(
            transformers.RemoveNonDataLines()
        )  # This was used only in get_row_data_from_lims_export
        controller.transform(transformers.WideToLong())
        controller.transform(
            transformers.ReplaceCommaWithDot()
        )  # This was used only in get_row_data_from_lims_export
        controller.transform(transformers.AddSampleDate())
        controller.transform(transformers.AddSampleTime())
        controller.transform(transformers.AddDatetime())
        controller.transform(transformers.AddVisitKey())
        controller.transform(transformers.AddAnalyseInfo())
        controller.transform(
            transformers.MoveLessThanFlagRowFormat()
        )  # This was used only in get_row_data_from_lims_export
        controller.transform(transformers.ConvertFlagsToSDN())
        controller.transform(transformers.RemoveColumns("COPY_VARIABLE.*"))
        controller.transform(
            transformers.MapperParameterColumn(import_column="SHARKarchive")
        )

    def _automatic_qc_callback(self, event):
        self._external_automatic_qc_callback()

    def _file_loaded(self):
        if self._file_name:
            file_info = f"<p>{self._file_name}</p>"
            self._qc_button.disabled = False
        else:
            file_info = "<p>No file loaded</p>"
            self._qc_button.disabled = True
        self._loaded_file_label.text = file_info

    def _save_file_as_callback(self, save_file_callback):
        try:
            root = tkinter.Tk()
            root.iconify()
            selected_path = tkinter.filedialog.asksaveasfilename(defaultextension=".csv")
            root.destroy()
        except tkinter.TclError:
            selected_path = None

        if not selected_path:
            return
        selected_path = Path(selected_path)
        save_file_callback(selected_path)

    @property
    def layout(self):
        return Column(
            self._load_header,
            self._file_button,
            self._loaded_file_label,
            self._save_as_button,
            self._save_changes_as_button,
            self._qc_header,
            self._qc_button,
        )
