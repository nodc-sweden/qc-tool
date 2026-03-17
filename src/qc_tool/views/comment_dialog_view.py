import typing

from bokeh.models import Button, Column, Dialog, Div, Row, Select, TextAreaInput
from ocean_data_qc.fyskem.qc_flag import QcFlag

from qc_tool.views.base_view import BaseView

if typing.TYPE_CHECKING:
    from qc_tool.controllers.comment_dialog_controller import CommentDialogController


class CommentDialogView(BaseView):
    DEFAULT_CATEGORY_VALUE = "Choose a category..."

    def __init__(self, controller: "CommentDialogController"):
        self._controller = controller
        self._controller._comment_dialog_view = self

        self._flag_label = Div()

        self._category_select = Select(
            title="Category",
            sizing_mode="stretch_width",
        )
        self._comment_input = TextAreaInput(
            title="Comment",
            value="",
            rows=5,
            sizing_mode="stretch_width",
        )
        self._ok_button = Button(label="OK")
        self._cancel_button = Button(label="Cancel")

        self._ok_button.on_click(self._on_ok_clicked)
        self._cancel_button.on_click(self._on_cancel_clicked)
        self._comment_input.on_change("value", self._on_input_changed)
        self._category_select.on_change("value", self._on_input_changed)

        self._dialog = Dialog(
            title="Manual QC comment",
            content=Column(
                self._flag_label,
                self._category_select,
                self._comment_input,
                Row(self._ok_button, self._cancel_button),
                sizing_mode="stretch_width",
            ),
            visible=False,
            closable=False,
            minimizable=False,
            maximizable=False,
            collapsible=False,
            pinnable=False,
            styles={"width": "350px", "height": "325px"},
        )

    def open(self, flag: QcFlag, categories: list[str]):
        self._flag_label.text = f"<h3>Flag: {flag}</h3>"
        self._category_select.options = [self.DEFAULT_CATEGORY_VALUE, *categories]
        self._category_select.value = self.DEFAULT_CATEGORY_VALUE
        self._comment_input.value = ""
        self._validate_input()
        self._dialog.visible = True

    def close(self):
        self._dialog.visible = False

    def _on_ok_clicked(self, _event):
        self._controller.on_ok(
            self._category_select.value,
            self._comment_input.value,
        )

    def _on_cancel_clicked(self, _event):
        self._controller.on_cancel()

    def _on_input_changed(self, _attr, _old, _new):
        self._validate_input()

    def _validate_input(self):
        category_not_selected = self._category_select.value == self.DEFAULT_CATEGORY_VALUE
        no_comment_selected = self._category_select.value == self._controller.NO_COMMENT
        if no_comment_selected:
            self._comment_input.value = ""
        self._comment_input.disabled = no_comment_selected or category_not_selected

        self._ok_button.disabled = category_not_selected

    @property
    def layout(self):
        return self._dialog
