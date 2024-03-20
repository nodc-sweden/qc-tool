from bokeh.models import Div
from station import Station


class StationInfo:
    STATION_DATA_FIELDS = (
        ("STATN", "Station name"),
        ("WADEP", "Water depth"),
        ("AIRTEMP", "Air temperature"),
        ("AIRPRES", "Air pressure"),
        ("WINDR", "Wind direction"),
        ("WINSP", "Wind speed"),
        ("COMNT_VISIT", "Comment"),
    )

    def __init__(self):
        self._div = Div(width=1000)
        self._station = None
        self._update()

    def set_station(self, station: Station):
        self._station = station
        self._update()

    def _update(self):
        table_rows = (
            f"""            <tr>
                <th>{title}</>
                <td>{self._station.common.get(column) if self._station else ""}</td>
            </tr>
"""
            for column, title in self.STATION_DATA_FIELDS
        )

        self._div.text = f"""
        <table>
            <tr>
                <th>Station</>
                <td>{self._station.name if self._station else ""}</td>
            </tr>
{''.join(table_rows)}        </table>
        """

    @property
    def div(self):
        return self._div
