from unittest.mock import MagicMock, patch

import polars as pl

from qc_tool.callback_queue import CallbackQueue
from qc_tool.controllers.file_controller import FileController
from qc_tool.models.ctd_file_model import CtdFileModel


def test_file_controller_can_load_ctd_data():
    # Given a CtdFileModel
    given_ctd_file_model = CtdFileModel(CallbackQueue())

    # Given a controller with a CtdFileModel
    given_controller = FileController(
        MagicMock(),
        given_ctd_file_model,
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    given_controller.file_view = MagicMock()

    # Given a listener on NEW_DATA for the CtdFileModel
    given_listener = MagicMock()
    given_controller.ctd_file_model.register_listener(
        CtdFileModel.NEW_DATA, given_listener
    )
    given_listener.assert_not_called()

    # Given that sharkadm returns a known dataframe for a given path
    given_data = pl.DataFrame({"DEPH": [1.0], "TEMP_CTD": [10.0]})
    mock_controller = MagicMock()
    mock_controller.export.return_value = given_data

    with patch(
        "qc_tool.controllers.file_controller.sharkadm_controller"
        ".get_polars_controller_with_data",
        return_value=mock_controller,
    ):
        # When loading the CTD file
        given_controller.load_ctd_file("some/path")

    # Then the CtdFileModel contains the data from sharkadm
    assert given_controller.ctd_file_model.data is given_data

    # And the listener is notified
    given_listener.assert_called_once()


def test_load_ctd_file_does_not_store_data_when_sharkadm_fails():
    # Given a CtdFileModel
    given_ctd_file_model = CtdFileModel(CallbackQueue())

    # Given a controller with a CtdFileModel
    given_controller = FileController(
        MagicMock(),
        given_ctd_file_model,
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    given_controller.file_view = MagicMock()

    # Given that sharkadm raises an exception for the given path
    with patch(
        "qc_tool.controllers.file_controller.sharkadm_controller"
        ".get_polars_controller_with_data",
        side_effect=Exception("load failed"),
    ):
        # When loading the CTD file
        given_controller.load_ctd_file("some/path")

    # Then the CtdFileModel data remains None
    assert given_ctd_file_model.data is None
