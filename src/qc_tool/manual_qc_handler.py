from bokeh.models import Div

from qc_tool.protocols import Layoutable


class ManualQcHandler(Layoutable):
    def __init__(self):
        self._div = Div(text="HEJ")

    @property
    def layout(self):
        return self._div
