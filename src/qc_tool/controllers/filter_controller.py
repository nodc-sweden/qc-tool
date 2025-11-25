from qc_tool.models.filter_model import FilterModel
from qc_tool.models.visits_model import VisitsModel
from qc_tool.views.filter_view import FilterView


class FilterController:
    def __init__(self, visits_model: VisitsModel, filter_model: FilterModel):
        self._visits_model = visits_model
        self._visits_model.register_listener(VisitsModel.NEW_VISITS, self._on_new_visits)

        self._filter_model = filter_model
        self._filter_model.register_listener(
            FilterModel.FILTER_OPTIONS_CHANGED, self._on_filter_options_changed
        )
        self._filter_model.register_listener(
            FilterModel.FILTER_CHANGED, self._on_filter_changed
        )

        self.filter_view: FilterView = None

    def _on_new_visits(self):
        self._filter_model.clear_all()
        self._filter_model.set_filter_options(
            years=self._visits_model.possible_years(self._filter_model),
            months=self._visits_model.possible_months(self._filter_model),
            cruises=self._visits_model.possible_cruises(self._filter_model),
            stations=self._visits_model.possible_stations(self._filter_model),
        )

    def _on_filter_changed(self):
        self._filter_model.set_filter_options(
            years=self._visits_model.possible_years(self._filter_model),
            months=self._visits_model.possible_months(self._filter_model),
            cruises=self._visits_model.possible_cruises(self._filter_model),
            stations=self._visits_model.possible_stations(self._filter_model),
        )

    def _on_filter_options_changed(self):
        self.filter_view.update_filter_options()
