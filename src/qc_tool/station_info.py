from bokeh.models import DataTable, Div, Styles, ImportedStyleSheet

from qc_tool.station import Station


class StationInfo:
    STATION_DATA_FIELDS = (
        ("STATN", "Station name"),
        ("CTRYID-SHIPC-CRUISE_NO-STNNO", "Country-Ship-Cruise-Series"),
        ("WADEP", "Water depth"),
        ("AIRTEMP", "Air temperature"),
        ("AIRPRES", "Air pressure"),
        ("WINDR", "Wind direction"),
        ("WINSP", "Wind speed"),
        ("COMNT_VISIT", "Comment"),
    )

    def __init__(self):
        self._table = DataTable()
        self._div = Div(width=500, stylesheets=[ImportedStyleSheet(url="qc_tool/static/css/style.css")])
        self._station = None
        self._update()

    def set_station(self, station: Station):
        self._station = station
        self._update()

    def _update(self):
        table_rows = (
            f"""<tr>
            <th>{title}</>
            <td>{self._station.common.get(column) if self._station else ""}</td>
            </tr>"""
            for column, title in self.STATION_DATA_FIELDS
        )

        self._div.text = f"""
        <table>
            {''.join(table_rows)}
        </table>
        """

    @property
    def layout(self):
        return self._div
