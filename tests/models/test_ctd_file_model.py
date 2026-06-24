from unittest.mock import MagicMock

import polars as pl

from qc_tool.callback_queue import CallbackQueue
from qc_tool.models.ctd_file_model import CtdFileModel


def test_ctd_file_model_starts_with_no_data():
    # When creating a CtdFileModel
    given_ctd_file_model = CtdFileModel(CallbackQueue())

    # Then it has no data
    assert given_ctd_file_model.data is None


def test_set_data_stores_data():
    # Given a CtdFileModel
    given_ctd_file_model = CtdFileModel(CallbackQueue())

    # Given a listener
    given_listener = MagicMock()
    given_ctd_file_model.register_listener(CtdFileModel.NEW_DATA, given_listener)
    given_listener.assert_not_called()

    # Given a CTD dataframe
    given_ctd_data = pl.DataFrame()

    # Given a file path
    given_file_path = "some/path"

    # When calling add_data with the data and the file path
    given_ctd_file_model.add_data(given_ctd_data, given_file_path)

    # Then the data is stored
    assert given_ctd_file_model.data is given_ctd_data

    # And the file path is stored
    assert given_file_path in given_ctd_file_model.file_paths

    # And the listener is notified
    given_listener.assert_called_once()
