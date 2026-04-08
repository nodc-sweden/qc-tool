from unittest.mock import ANY, MagicMock

import pytest
from ocean_data_qc.fyskem.qc_flag import QcFlag

from qc_tool.callback_queue import CallbackQueue
from qc_tool.controllers.comment_dialog_controller import CommentDialogController
from qc_tool.models.manual_qc_model import ManualQcModel


def make_controller():
    queue = CallbackQueue()
    model = ManualQcModel(queue)
    controller = CommentDialogController(model)
    controller._comment_dialog_view = MagicMock()
    return controller, model


@pytest.mark.parametrize(
    "given_comment, expected_comment",
    [
        ("  A comment.  ", "A comment."),
        ("", ""),
        ("   ", ""),
        ("A    comment.", "A    comment."),
    ],
)
def test_on_ok_calls_confirm_flag_with_stripped_comment(given_comment, expected_comment):
    # Given a CommentDialogController with mocked CommentDialogModel
    controller, model = make_controller()

    # Given a mocked ManualQcModel
    model.confirm_flag = MagicMock()

    # When calling on_ok
    controller.on_ok(QcFlag.PROBABLY_GOOD_VALUE, "ANY CATEGORY", given_comment)

    # Then the model is called with the expected comment
    model.confirm_flag.assert_called_once_with(ANY, ANY, expected_comment)
