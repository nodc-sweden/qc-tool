import abc

from bokeh.models import UIElement


class BaseView(abc.ABC):
    @abc.abstractmethod
    def layout(self) -> UIElement:
        pass
