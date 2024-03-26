from typing import Protocol

from bokeh.models import UIElement


class Layoutable(Protocol):
    def layout(self) -> UIElement:
        pass
