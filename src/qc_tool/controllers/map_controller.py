from pyproj import Transformer

from qc_tool.models.map_model import MapModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.map_view import MapView


class MapController:
    margin_ratio = 1.25

    def __init__(
        self, visits_model: VisitsModel | None = None, map_model: MapModel | None = None
    ):
        self._visits_model = visits_model
        self._visits_model.register_listener(
            self._visits_model.NEW_VISITS, self._visits_updated
        )
        self._visits_model.register_listener(
            VisitsModel.VISIT_SELECTED, self._visit_selected
        )

        self._map_model = map_model
        self._transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")
        self.map_view: MapView = None

    def select_visit(self, station_visit: str):
        self._visits_model.set_visit_by_key(station_visit)

    def _visits_updated(self):
        all_stations = [
            (visit.visit_key, visit.longitude, visit.latitude)
            for visit in self._visits_model.visits.values()
        ]

        station_names, longitudes, latitudes = zip(*all_stations)
        longitudes, latitudes = self._convert_projection(longitudes, latitudes)

        visit_points = {
            "longitudes": longitudes,
            "latitudes": latitudes,
            "visit_keys": station_names,
        }
        self._map_model.set_points(visit_points)
        self._zoom_to_points()

    def _visit_selected(self):
        self._map_model.set_selection([self._visits_model.selected_visit.visit_key])

    def _convert_projection(self, longitudes, latitudes):
        if not longitudes or not latitudes:
            return longitudes, latitudes

        transformed_longitudes, transformed_latitudes = self._transformer.transform(
            yy=longitudes,
            xx=latitudes,
        )

        return transformed_longitudes, transformed_latitudes

    def _zoom_to_points(self):
        x_min = min(self._map_model.unselected.data["longitudes"])
        x_max = max(self._map_model.unselected.data["longitudes"])
        y_min = min(self._map_model.unselected.data["latitudes"])
        y_max = max(self._map_model.unselected.data["latitudes"])

        data_width = (x_max - x_min) * self.margin_ratio
        data_height = (y_max - y_min) * self.margin_ratio

        center_x = (x_max + x_min) / 2
        center_y = (y_max + y_min) / 2

        plot_ratio = self.map_view.width / self.map_view.height
        data_ratio = data_width / data_height

        if data_ratio > plot_ratio:
            data_height = data_width / plot_ratio
        else:
            data_width = data_height * plot_ratio

        x_start = center_x - data_width / 2
        x_end = center_x + data_width / 2
        y_start = center_y - data_height / 2
        y_end = center_y + data_height / 2

        self.map_view.set_position(x_start, x_end, y_start, y_end)
