from qc_tool.controllers.file_controller import FileController
from qc_tool.controllers.map_controller import MapController
from qc_tool.controllers.validation_log_controller import ValidationLogController
from qc_tool.models.file_model import FileModel
from qc_tool.models.map_model import MapModel
from qc_tool.models.validation_log_model import ValidationLogModel
from qc_tool.models.visits_model import VisitsModel


class SummaryController:
    def __init__(
        self,
        file_model: FileModel,
        visits_model: VisitsModel,
        map_model: MapModel,
        validation_log_model: ValidationLogModel,
    ):
        self._file_model = file_model
        self._visits_model = visits_model
        self._validation_log_model = validation_log_model

        self.file_controller = FileController(
            self._file_model, self._validation_log_model
        )

        self.map_controller = MapController(self._visits_model, map_model)
        self.validation_log_controller = ValidationLogController(
            self._validation_log_model
        )
