from unittest.mock import MagicMock

import pytest
from ocean_data_qc.fyskem.parameter import Parameter
from ocean_data_qc.fyskem.qc_flag import QcFlag

from qc_tool.callback_queue import CallbackQueue
from qc_tool.models.manual_qc_model import ManualQcModel


@pytest.fixture
def given_manual_qc_model():
    queue = CallbackQueue()
    return ManualQcModel(queue)


def make_manual_qc_model_with_a_selected_value():
    queue = CallbackQueue()
    model = ManualQcModel(queue)
    value = Parameter({"parameter": "TEMP_BTL", "value": 5.0, "DEPH": 10.0})
    model._selected_values = [value]
    model._parameter_index = 0
    model._value_index = (0,)
    model._last_sender = MagicMock()
    return model, value


@pytest.mark.parametrize(
    "given_flag", (QcFlag.BAD_VALUE, QcFlag.GOOD_VALUE, QcFlag.PROBABLY_GOOD_VALUE)
)
def test_request_flag_sets_pending_flag(given_manual_qc_model, given_flag):
    # When requesting a given flag
    given_manual_qc_model.request_flag(given_flag)

    # Then the pending flag is set
    assert given_manual_qc_model.pending_flag == given_flag


def test_cancel_flag_aborts_manual_qc():
    # Given a ManualQcModel and a selected value
    given_manual_qc_model, given_value = make_manual_qc_model_with_a_selected_value()

    # Given a listener on QC_PERFORMED
    given_listener = MagicMock()
    given_manual_qc_model.register_listener(ManualQcModel.QC_PERFORMED, given_listener)

    # Given the model has a pending flag
    given_flag = QcFlag.BAD_VALUE
    given_manual_qc_model.request_flag(given_flag)

    # When cancelling the flag
    given_manual_qc_model.cancel_flag()

    # Then the flag is not assigned to the value
    assert given_value.qc.manual != given_flag

    # And QC_PERFORMED is not emitted
    given_listener.assert_not_called()

    # And the pending flag is removed
    assert given_manual_qc_model.pending_flag is None


@pytest.mark.parametrize(
    "given_flag, given_category, given_comment",
    [
        (QcFlag.BAD_VALUE, "A category", "A comment."),
        (QcFlag.PROBABLY_BAD_VALUE, "cAtEgOry", "cOmMeNt"),
        (QcFlag.GOOD_VALUE, "", ""),
    ],
)
def test_confirm_flag_stores_flag_category_and_comment(
    given_flag, given_category, given_comment
):
    # Given a ManualQcModel and a selected value
    given_manual_qc_model, given_value = make_manual_qc_model_with_a_selected_value()

    # Given a listener on QC_PERFORMED
    given_listener = MagicMock()
    given_manual_qc_model.register_listener(ManualQcModel.QC_PERFORMED, given_listener)

    # Given the model has a pending flag
    given_manual_qc_model.request_flag(given_flag)

    # When confirming the flag
    given_manual_qc_model.confirm_flag(given_category, given_comment)

    # Then the flag is assigned to the value
    assert given_value.qc.manual == given_flag

    # And the category and comment are stored as-is
    assert given_manual_qc_model.comment_category == given_category
    assert given_manual_qc_model.comment == given_comment

    # And QC_PERFORMED is emitted
    given_listener.assert_called_once()

    # And the pending flag is reset
    assert given_manual_qc_model.pending_flag is None
