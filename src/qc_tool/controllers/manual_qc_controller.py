from qc_tool.models.manual_qc_model import ManualQcModel


class ManualQcController:
    def __init__(self, manual_qc_model: ManualQcModel):
        self.manual_qc_model = manual_qc_model
        self.manual_qc_view = None

    def set_flag(self, new_flag):
        self.manual_qc_model.request_flag(new_flag)
