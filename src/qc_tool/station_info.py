from collections import defaultdict

import jinja2
from bokeh.models import DataTable, Div, ImportedStyleSheet
from ocean_data_qc.metadata.metadata_flag import MetadataFlag

from qc_tool.layoutable import Layoutable
from qc_tool.station import Station

_metadata_template = jinja2.Template("""
    <table>
        {% for key, value, class in metadata %}
        <tr class="{{ class }}">
            <th>{{ key }}</th>
            <td class="metadata-value">{{ value }}</td>
            <td class="metadata-status"></td>
        </tr>
        {% endfor %}
    </table>
""")

_class_from_status = {
    MetadataFlag.NO_QC_PERFORMED: "no-qc-performed",
    MetadataFlag.GOOD_DATA: "good-data",
    MetadataFlag.BAD_DATA: "bad-data",
}


class StationInfo(Layoutable):
    STATION_DATA_FIELDS = (
        ("STATN", "Station name"),
        ("SERNO", "Series"),
        ("CTRYID+SHIPC+CRUISE_NO", "Country-Ship-Cruise"),
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
        self.update()

    def set_station(self, station: Station):
        self._station = station
        self.update()

    def update(self):
        if self._station:
            common_data = self._station.common if self._station else {}
            checks_per_field = defaultdict(set)
            for check, fields in self._station._visit.qc_log.items():
                for field in fields:
                    checks_per_field[field].add(check)

            status_per_field = {
                field: max(self._station._visit.qc[check] for check in checks)
                for field, checks in checks_per_field.items()
            }

            metadata = [
                (
                    header,
                    common_data.get(key, ""),
                    _class_from_status[
                        max(
                            status_per_field.get(sub_key, MetadataFlag.NO_QC_PERFORMED)
                            for sub_key in key.split("+")
                        )
                    ],
                )
                for key, header in StationInfo.STATION_DATA_FIELDS
            ]
        else:
            metadata = [
                (header, "", "no-qc-performed") for _, header in self.STATION_DATA_FIELDS
            ]
        self._div.text = _metadata_template.render(metadata=metadata)

    @property
    def layout(self):
        return self._div
