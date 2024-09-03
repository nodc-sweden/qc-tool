import jinja2
from bokeh.models import DataTable, Div, ImportedStyleSheet

from qc_tool.layoutable import Layoutable
from qc_tool.station import Station

_metadata_template = jinja2.Template("""
        <table>
            {% for key,title in station_data_fields %}
            <tr>
            <th>{{ title }}</th>
            <td {% if station is not none and station._visit.qc.WADEP is defined %} class="test" {% endif %}>
            {{ common_data.get(key, "") }}</td>
            </tr>
            {% endfor %}
        </table>        
""")


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
        print(station._visit.qc)

    def _update(self):
        common_data = self._station.common if self._station else {}
        self._div.text = _metadata_template.render(
            station=self._station,
            station_data_fields=self.STATION_DATA_FIELDS,
            common_data=common_data,
        )

    @property
    def layout(self):
        return self._div
