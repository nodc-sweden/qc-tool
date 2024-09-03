import jinja2
import pandas as pd
from ocean_data_qc.metadata.metadata_flag import MetadataFlag
from ocean_data_qc.metadata.metadata_qc_field import MetadataQcField
from qc_tool.station import Station

_metadata_template = jinja2.Template("""
<table>{% for key, value, class in metadata %}
    <tr>
        <th>{{ key }}</th>
        <td class="{{ class }}">{{ value }}</td>
    </tr>{% endfor %}
</table>
""")

data = pd.DataFrame([{"parameter": "SYRE", "SERNO": "123", "STATN": "Norrköping"}])
_station = Station(None, data, None)
_station._visit.qc[MetadataQcField.Wadep] = MetadataFlag.BAD_DATA
print(_station._visit.qc)


STATION_DATA_FIELDS = (
    ("STATN", "Station name"),
    ("WADEP", "Water depth"),
    ("AIRTEMP", "Air temperature"),
)


metadata_fields_to_name = {"WADEP": MetadataQcField.Wadep}

common_data = {"STATN": "Norrköping", "WADEP": 123, "AIRTEMP": 24}

class_from_status = {
    MetadataFlag.NO_QC_PERFORMED: "no-qc-performed",
    MetadataFlag.GOOD_DATA: "good-data",
    MetadataFlag.BAD_DATA: "bad-data",
}

metadata = [
    (
        value,
        common_data[key],
        class_from_status[_station._visit.qc[metadata_fields_to_name[key]]]
        if key in metadata_fields_to_name
        else "no-qc-performed",
    )
    for key, value in STATION_DATA_FIELDS
]

print(_metadata_template.render(metadata=metadata))
