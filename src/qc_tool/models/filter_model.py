import polars as pl

from qc_tool.models.base_model import BaseModel
from qc_tool.models.file_model import FileModel
from qc_tool.visit import Visit


class FilterModel(BaseModel):
    FILTER_OPTIONS_CHANGED = "FILTER_OPTIONS_CHANGED"
    FILTER_CHANGED = "FILTER_CHANGED"

    def __init__(self, file_model: FileModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_model = file_model
        self._files = set()
        self._years = set()
        self._months = set()
        self._cruises = set()
        self._basins = set()
        self._stations = set()
        self._filtered_files = set()
        self._filtered_years = set()
        self._filtered_months = set()
        self._filtered_cruises = set()
        self._filtered_basins = set()
        self._filtered_stations = set()
        self._filtered_data = pl.DataFrame()

    def clear_all(self):
        self._files.clear()
        self._years.clear()
        self._months.clear()
        self._cruises.clear()
        self._basins.clear()
        self._stations.clear()
        self._filtered_files.clear()
        self._filtered_months.clear()
        self._filtered_cruises.clear()
        self._filtered_basins.clear()
        self._filtered_stations.clear()

        self._notify_listeners(self.FILTER_OPTIONS_CHANGED)

    def set_filter_options(
        self,
        files: set | None = None,
        years: set | None = None,
        months: set | None = None,
        cruises: set | None = None,
        stations: set | None = None,
        basins: set | None = None,
    ):
        if files is not None:
            self._files = files
        if years is not None:
            self._years = years
        if months is not None:
            self._months = months
        if stations is not None:
            self._stations = stations
        if cruises is not None:
            self._cruises = cruises
        if basins is not None:
            self._basins = basins

        self._notify_listeners(self.FILTER_OPTIONS_CHANGED)

    @property
    def file_paths(self):
        return self._file_model.file_paths

    @property
    def files(self):
        return [str(p) for p in self._file_model.file_paths if str(p) in self._files]

    @property
    def years(self):
        return sorted(self._years, key=lambda x: (x is None, x))

    @property
    def months(self):
        return sorted(self._months, key=lambda x: (x is None, x))

    @property
    def stations(self):
        return sorted(self._stations)

    @property
    def cruises(self):
        return sorted(self._cruises)

    @property
    def basins(self):
        return sorted(self._basins, key=lambda x: (x is None, x))

    @property
    def filtered_data(self):
        return self._filtered_data

    @filtered_data.setter
    def filtered_data(self, data):
        if data is None or data.is_empty():
            self._filtered_data = pl.DataFrame()
        else:
            self._filtered_data = data.filter(self.filtered_data_expression())

    def set_file_filter(self, files):
        self._filtered_files = set(files)
        if self._file_model.data is not None:
            self.filtered_data = self._file_model.data
        self._notify_listeners(self.FILTER_CHANGED)

    def set_year_filter(self, years):
        self._filtered_years = set(years)
        if self._file_model.data is not None:
            self.filtered_data = self._file_model.data
        self._notify_listeners(self.FILTER_CHANGED)

    def set_month_filter(self, months):
        self._filtered_months = set(months)
        if self._file_model.data is not None:
            self.filtered_data = self._file_model.data
        self._notify_listeners(self.FILTER_CHANGED)

    def set_cruise_filter(self, cruises):
        self._filtered_cruises = set(cruises)
        if self._file_model.data is not None:
            self.filtered_data = self._file_model.data
        self._notify_listeners(self.FILTER_CHANGED)

    def set_station_filter(self, stations):
        self._filtered_stations = set(stations)
        if self._file_model.data is not None:
            self.filtered_data = self._file_model.data
        self._notify_listeners(self.FILTER_CHANGED)

    def set_basin_filter(self, basins):
        self._filtered_basins = set(basins)
        if self._file_model.data is not None:
            self.filtered_data = self._file_model.data
        self._notify_listeners(self.FILTER_CHANGED)

    def filtered_data_expression(self):
        expr = pl.lit(True)
        if self._filtered_files:
            expr &= pl.col("source").is_in(list(self._filtered_files))
        if self._filtered_years:
            expr &= pl.col("MYEAR").is_in(list(self._filtered_years))
        if self._filtered_months:
            expr &= pl.col("visit_month").is_in(list(self._filtered_months))
        if self._filtered_cruises:
            expr &= pl.col("CRUISE_NO").is_in(list(self._filtered_cruises))
        if self._filtered_stations:
            expr &= pl.col("STATN").is_in(list(self._filtered_stations))
        if self._filtered_basins:
            non_null_basins = [b for b in self._filtered_basins if b is not None]
            includes_none = None in self._filtered_basins
            basin_expr = pl.lit(False)
            if non_null_basins:
                basin_expr |= pl.col("sea_basin").is_in(non_null_basins)
            if includes_none:
                basin_expr |= pl.col("sea_basin").is_null()
            expr &= basin_expr
        return expr

    def matches(
        self,
        visit: Visit,
        ignore_file: bool = False,
        ignore_year: bool = False,
        ignore_month: bool = False,
        ignore_cruise: bool = False,
        ignore_station: bool = False,
        ignore_basin: bool = False,
    ):
        def _field_matches(value, filtered_values: set, ignore: bool):
            return ignore or not filtered_values or value in filtered_values

        return (
            _field_matches(visit.file_path, self._filtered_files, ignore_file)
            and _field_matches(visit.year, self._filtered_years, ignore_year)
            and _field_matches(visit.month, self._filtered_months, ignore_month)
            and _field_matches(visit.cruise_number, self._filtered_cruises, ignore_cruise)
            and _field_matches(
                visit.station_name, self._filtered_stations, ignore_station
            )
            and _field_matches(visit.sea_basin, self._filtered_basins, ignore_basin)
        )
