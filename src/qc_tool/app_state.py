from qc_tool.callback_queue import CallbackQueue
from qc_tool.models.file_model import FileModel
from qc_tool.models.map_model import MapModel
from qc_tool.models.parameters_model import ParametersModel
from qc_tool.models.profiles_grid_model import ProfileGridModel
from qc_tool.models.validation_log_model import ValidationLogModel
from qc_tool.models.visits_model import VisitsModel


class AppState:
    def __init__(self):
        self._message_queue = CallbackQueue()
        self.file = FileModel(self._message_queue)
        self.visits = VisitsModel(self._message_queue)
        self.map = MapModel(self._message_queue)
        self.validation_log = ValidationLogModel(self._message_queue)
        self.parameters = ParametersModel(self._message_queue)
        self.profile_grid = ProfileGridModel(2, 5, self._message_queue)
