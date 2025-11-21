from qc_tool.models.base_model import BaseModel


class GeoInfoModel(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._geo_info = None

    @property
    def geo_info(self):
        return self._geo_info

    @geo_info.setter
    def geo_info(self, geo_info):
        self._geo_info = geo_info
