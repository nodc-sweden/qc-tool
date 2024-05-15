from bokeh.models import DataTable, Div, ImportedStyleSheet

from qc_tool.protocols import Layoutable
from qc_tool.station import Station


class StationInfo(Layoutable):
    STATION_DATA_FIELDS = (
        ("STATN", "Station name"),
        ("CTRYID+SHIPC+CRUISE_NO+SERNO", "Country-Ship-Cruise-Series"),
        ("SDATE+STIME", "Time"),
        ("WADEP", "Water depth"),
        ("AIRTEMP", "Air temperature"),
        ("AIRPRES", "Air pressure"),
        ("WINDIR", "Wind direction"),
        ("WINSP", "Wind speed"),
        ("COMNT_VISIT", "Comment"),
        ("LATIT", "Latitude"),
        ("LONGI", "Longitude"),
    )

    def __init__(self):
        self._table = DataTable()
        self._div = Div(
            width=500,
            stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")],
        )
        self._station = None
        self._update()

    def set_station(self, station: Station):
        self._station = station
        self._update()

    def _update(self):
        common_data = self._station.common if self._station else {}
        table_rows = (
            f"""<tr>
            <th>{title}</>
            <td>{common_data.get(key, "")}</td>
            </tr>"""
            for key, title in self.STATION_DATA_FIELDS
        )

        self._div.text = f"""
        <table>
            {''.join(table_rows)}
        </table>
        """

    @property
    def layout(self):
        return self._div
