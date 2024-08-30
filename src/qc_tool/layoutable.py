import abc

from bokeh.models import UIElement


class Layoutable(abc.ABC):
    @abc.abstractmethod
    def layout(self) -> UIElement:
        pass
