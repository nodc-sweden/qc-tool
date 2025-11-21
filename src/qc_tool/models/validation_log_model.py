from qc_tool.models.base_model import BaseModel


class ValidationLogModel(BaseModel):
    NEW_VALIDATION_LOG = "NEW_VALIDATION_LOG"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validation_log = None

    def set_validation_log(self, validation_log):
        self._validation_log = validation_log
        self._notify_listeners(self.NEW_VALIDATION_LOG)

    @property
    def validation_log(self):
        return self._validation_log
