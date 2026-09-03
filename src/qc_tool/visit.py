import polars as pl
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flags import QcFlags


class Visit:
    COMMON_COLUMNS = frozenset(
        {
            "AIRPRES",
            "AIRTEMP",
            "COMNT_VISIT",
            "CRUISE_NO",
            "LATIT",
            "LONGI",
            "sample_latitude_dd",
            "sample_longitude_dd",
            "SDATE",
            "SHIPC",
            "STATN",
            "STIME",
            "SERNO",
            "WADEP",
            "WINDIR",
            "WINSP",
        }
    )

    def __init__(
        self, visit_key: str, data: pl.DataFrame, ctd_data: pl.DataFrame | None = None
    ):
        self._visit_key = visit_key
        self._data = data
        self._ctd_data = (
            ctd_data if ctd_data is not None and not ctd_data.is_empty() else None
        )

        self._common = {
            column: self._data[column].unique().to_list()[0]
            for column in self.COMMON_COLUMNS
            if column in self._data.columns
        }

        self._parameters = sorted(self._data["parameter"].unique().to_list())
        self._row_numbers = sorted(self._data["row_number"].unique().to_list())

        if "sea_basin" in self._data.columns:
            self._sea_basin = self._data["sea_basin"].unique().to_list()[0]
        else:
            self._sea_basin = None

        self._max_depth = self._data["DEPH"].max()

        self.validation_logs = []
        self._parameter_data: dict[str, dict | None] = {}

    def parameter_data(self, parameter: str):
        if parameter not in self._parameter_data:
            self._parameter_data[parameter] = self._build_parameter_data(parameter)

        return self._parameter_data[parameter]

    def _build_parameter_data(self, parameter: str) -> dict | None:
        parameter_data = self._data.filter(pl.col("parameter") == parameter).sort("DEPH")

        if parameter_data.is_empty():
            return None

        # TODO: could this be more efficient?
        # raw QC
        # → QcFlags
        # → string
        # → QcFlags again
        if "quality_flag_long" not in parameter_data.columns:
            parameter_data = parameter_data.with_columns(
                quality_flag_long=pl.col("quality_flag").map_elements(
                    lambda x: str(QcFlags(QcFlag.parse(x), None, None, None)),
                    return_dtype=pl.Utf8,
                )
            )

        parameter_data = parameter_data.with_columns(
            quality_flag=pl.struct("quality_flag_long").map_elements(
                lambda row: QcFlags.from_string(row["quality_flag_long"]).total.value,
                return_dtype=pl.Utf8,
            )
        )

        qc_flags = list(map(QcFlags.from_string, parameter_data["quality_flag_long"]))

        colors = [
            QC_FLAG_CSS_COLORS.get(QcFlag.parse(flag))
            for flag in parameter_data["quality_flag"]
        ]

        line_colors = [
            "black" if flags.incoming.value != flags.total.value else "none"
            for flags in qc_flags
        ]

        return {
            "x": list(parameter_data["value"]),
            "unit": list(parameter_data["unit"]),
            "y": list(parameter_data["DEPH"]),
            "color": colors,
            "line_color": line_colors,
            "qc": [f"{flags.total} ({flags.total.value})" for flags in qc_flags],
            "qc_incoming": [
                f"{flags.incoming} ({flags.incoming.value})" for flags in qc_flags
            ],
            "qc_automatic": [
                f"{flags.total_automatic} {flags.total_automatic_name}"
                for flags in qc_flags
            ],
            "qc_manual": [f"{flags.manual} ({flags.manual.value})" for flags in qc_flags],
            "data": parameter_data,
        }

    @property
    def parameters(self) -> list[str]:
        return self._parameters

    @property
    def depths(self) -> list[float]:
        return sorted(self._data["DEPH"].unique().to_list())

    @property
    def row_numbers(self) -> list[str]:
        return self._row_numbers

    @property
    def sea_basin(self):
        return self._sea_basin

    @property
    def file_path(self):
        return self._data.select("source").to_series()[0]

    @property
    def data(self) -> pl.DataFrame:
        return self._data

    @property
    def datetime(self):
        return self._data.select("datetime").to_series()[0]

    @property
    def year(self):
        return self._data.select("MYEAR").to_series()[0]

    @property
    def month(self):
        return self._data.select("visit_month").to_series()[0]

    @property
    def country_ship_cruise_visit_key(self):
        return "-".join(
            [str(self._common.get(key)) for key in ("CTRYID", "SHIPC", "CRUISE_NO")]
            + [self._visit_key]
        )

    @property
    def country_ship_cruise(self) -> str:
        return "-".join(
            [str(self._common.get(key)) for key in ("CTRYID", "SHIPC", "CRUISE_NO")]
        )

    @property
    def serno(self) -> str:
        return self._get_serno()

    @property
    def visit_key(self) -> str:
        return self._visit_key

    @property
    def common(self) -> dict:
        compound_values = {
            "SDATE+STIME": self.datetime,
            "CTRYID+SHIPC+CRUISE_NO+VISITKEY": self.country_ship_cruise_visit_key,
            "CTRYID+SHIPC+CRUISE_NO": self.country_ship_cruise,
        }
        return self._common | compound_values

    @property
    def station_name(self) -> str:
        return self._common.get("STATN")

    @property
    def cruise_number(self) -> str:
        return self._common.get("CRUISE_NO")

    @property
    def water_depth(self) -> float:
        return self._common.get("WADEP")

    @property
    def max_depth(self) -> float:
        return self._max_depth

    @property
    def longitude(self) -> float:
        return self._common.get("sample_longitude_dd")

    @property
    def latitude(self) -> float:
        return self._common.get("sample_latitude_dd")

    @property
    def has_ctd_data(self) -> bool:
        return self._ctd_data is not None

    def ctd_data_for_parameter(self, parameter: str):
        if self._ctd_data is not None:
            ctd_parameter = parameter.replace("BTL", "CTD")
            if ctd_parameter in self._ctd_data.columns:
                columns = (
                    ["DEPTH_CTD", pl.col(ctd_parameter).cast(pl.Float64)]
                    if ctd_parameter != "DEPTH_CTD"
                    else [pl.col(ctd_parameter).cast(pl.Float64)]
                )
                return self._ctd_data.select(columns)
        return None

    def _get_serno(self) -> str:
        """
        this avoids missing errors/cases where a visit_key has >1 serno.
        add a validator for this in sharkadm if not already exists.
        """
        if "SERNO" not in self._data.columns:
            return ""

        sernos = self._data.get_column("SERNO").drop_nulls().cast(pl.String).to_list()

        sernos = sorted({serno for serno in sernos if serno})

        return ", ".join(sernos)
