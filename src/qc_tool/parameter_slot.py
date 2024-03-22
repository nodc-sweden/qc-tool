import numpy as np
from bokeh.layouts import column
from bokeh.models import BoxAnnotation, ColumnDataSource, Dropdown, WheelZoomTool
from bokeh.plotting import figure

from qc_tool.station import Station


class ParameterSlot:
    def __init__(
        self,
        parameter: str = None,
        linked_y_range=None,
        default_parameter: str = None,
    ):
        self._default_parameter = default_parameter
        self._parameter = parameter or self._default_parameter
        self._station = None
        self._source = ColumnDataSource(data={"x": [], "y": []})

        wheel_zoom = WheelZoomTool()
        self._figure_config = {
            "height": 500,
            "width": 500,
            "toolbar_location": "below",
            "tools": ["pan", wheel_zoom, "reset"],
        }

        self._plot_config = {
            "size": 7,
            "color": "navy",
            "alpha": 0.8,
        }

        self._figure = figure(**self._figure_config)
        self._figure.toolbar.active_scroll = wheel_zoom

        #self._figure.image_url(url=["qc_tool/static/images/gull.png"], x=0, y=-500)
        sea_level = BoxAnnotation(bottom=0, fill_color="lightskyblue", fill_alpha=0.10)
        sea_level.level = "underlay"
        self._figure.add_layout(sea_level)

        # Add ocean floor but hide it until there is a level
        self._ocean_floor = BoxAnnotation(fill_color="saddlebrown", fill_alpha=0.75)
        self._ocean_floor.level = "underlay"
        self._figure.add_layout(self._ocean_floor)
        self._ocean_floor.visible = False

        self._figure.scatter("x", "y", source=self._source, **self._plot_config)
        if linked_y_range:
            self._figure.y_range = linked_y_range
        else:
            self._figure.y_range.flipped = True

        self._parameter_dropdown = Dropdown(
            label=self._parameter or "Parameter",
            button_type="default",
            menu=[],
            name="parameter",
            width=200,
        )

        self._parameter_dropdown.on_click(self.parameter_selected)

    def update_station(self, station: Station):
        self._station = station
        self._parameter_dropdown.menu = self._station.parameters
        y = self._station.data.index
        if self._parameter in self._station.parameters:
            x = self._station.data[self._parameter]
            self._parameter_dropdown.label = self._parameter
        else:
            x = [np.nan] * len(y)

        self._source.data = {"x": x, "y": y}

        if water_depth := self._station.water_depth:
            self._ocean_floor.top = water_depth
            self._ocean_floor.visible = True
        else:
            self._ocean_floor.visible = False

    def parameter_selected(self, event):
        self._parameter = event.item
        self._source.data["x"] = self._station.data[self._parameter]
        self._parameter_dropdown.label = self._parameter

    @property
    def layout(self):
        return column(
            self._parameter_dropdown,
            self._figure,
        )

    @property
    def y_range(self):
        return self._figure.y_range
