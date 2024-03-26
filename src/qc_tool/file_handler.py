import io
from base64 import b64decode

import pandas as pd
from bokeh.models import Column, Div, FileInput

from qc_tool.protocols import Layoutable


class FileHandler(Layoutable):
    def __init__(self, external_load_file_callback):
        self._file_name = None
        self._external_load_file_callback = external_load_file_callback
        self._div = Div(width=500)
        self._file_input = FileInput(
            title="Select file:", accept=".txt,.json", max_width=500
        )
        self._file_input.on_change("filename", self._internal_load_file_callback)
        self._update_info()

    def _internal_load_file_callback(self, attr, old, new):
        self._file_name = new
        encoded_bytes = self._file_input.value
        decoded_bytes = b64decode(encoded_bytes)
        byte_buffer = io.BytesIO(decoded_bytes)

        data = pd.read_csv(byte_buffer, sep="\t")
        self._external_load_file_callback(data)
        self._update_info()

    def _update_info(self):
        if self._file_name:
            file_info = f"<h3>{self._file_name}</h3>"
        else:
            file_info = "<h3>No file loaded</h3>"
        self._div.text = file_info

    @property
    def layout(self):
        return Column(self._file_input, self._div)
