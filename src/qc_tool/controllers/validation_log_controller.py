from qc_tool.models.validation_log_model import ValidationLogModel


class ValidationLogController:
    def __init__(self, validation_log_model: ValidationLogModel):
        self._validation_log_model = validation_log_model
        self._validation_log_model.register_listener(
            ValidationLogModel.NEW_VALIDATION_LOG, self._on_new_validation_log
        )

        self.validation_log_view = None

    def _on_new_validation_log(self):
        self._validation_log = self._validation_log_model.validation_log
        self.validation_log_view.update(self._validation_log_model.validation_remarks)
