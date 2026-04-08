import typing

from bokeh.models import (
    Button,
    Column,
    Dialog,
    Div,
    RadioButtonGroup,
    Row,
    Select,
    TextAreaInput,
)
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag

from qc_tool.views.base_view import BaseView

if typing.TYPE_CHECKING:
    from qc_tool.controllers.comment_dialog_controller import CommentDialogController


class CommentDialogView(BaseView):
    DEFAULT_CATEGORY_VALUE = "Choose a category..."
    AVAILABLE_FLAGS = (
        QcFlag("1"),
        QcFlag("2"),
        QcFlag("3"),
        QcFlag("4"),
        QcFlag("7"),
        QcFlag("Q"),
    )

    def __init__(self, controller: "CommentDialogController"):
        self._controller = controller
        self._controller._comment_dialog_view = self

        self._flag_header = Div(text="<h3>QC Flag</h3>")
        self._qc_flag_buttons = [
            flag for flag in self.AVAILABLE_FLAGS if QC_FLAG_CSS_COLORS[flag] != "gray"
        ]

        self._qc_buttons = RadioButtonGroup(
            labels=[str(flag) for flag in self._qc_flag_buttons],
            orientation="vertical",
            active=None,
        )
        self._flag_section = Column(self._flag_header, self._qc_buttons)

        self._comment_header = Div(text="<h3>Comment</h3>")

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
        self._commment_section = Column(
            self._comment_header,
            self._category_select,
            self._comment_input,
            styles={"width": "300px"},
        )

        self._ok_button = Button(label="OK")
        self._cancel_button = Button(label="Cancel")

        self._ok_button.on_click(self._on_ok_clicked)
        self._cancel_button.on_click(self._on_cancel_clicked)

        self._qc_buttons.on_change("active", self._on_input_changed)
        self._comment_input.on_change("value", self._on_input_changed)
        self._category_select.on_change("value", self._on_input_changed)

        self._dialog = Dialog(
            title="Manual QC comment",
            content=Row(
                self._flag_section,
                Column(
                    self._commment_section,
                    Row(
                        self._ok_button,
                        self._cancel_button,
                        styles={"justify-content": "flex-end", "width": "100%"},
                    ),
                    sizing_mode="stretch_width",
                    spacing=30,
                ),
                spacing=30,
            ),
            visible=False,
            closable=False,
            minimizable=False,
            maximizable=False,
            collapsible=False,
            pinnable=False,
            styles={"width": "fit-content", "height": "fit-content"},
        )

    def open(self):
        categories = self._controller._categories_for_flag(None)
        self._category_select.options = [self.DEFAULT_CATEGORY_VALUE, *categories]
        self._category_select.value = self.DEFAULT_CATEGORY_VALUE
        self._comment_input.value = ""
        self._validate_input()
        self._dialog.visible = True

    def close(self):
        self._dialog.visible = False

    def _on_ok_clicked(self, _event):
        self._controller.on_ok(
            self.selected_flag,
            self._category_select.value,
            self._comment_input.value,
        )

    def _on_cancel_clicked(self, _event):
        self._controller.on_cancel()

    def _on_input_changed(self, _attr, _old, _new):
        self._validate_input()

    def _validate_input(self):
        self._category_select.options = [
            self.DEFAULT_CATEGORY_VALUE,
            *self._controller._categories_for_flag(self.selected_flag),
        ]

        no_flag_selected = self._qc_buttons.active is None
        category_not_selected = self._category_select.value == self.DEFAULT_CATEGORY_VALUE
        no_comment_selected = self._category_select.value == self._controller.NO_COMMENT
        if no_comment_selected:
            self._comment_input.value = ""
        self._comment_input.disabled = no_comment_selected or category_not_selected

        self._ok_button.disabled = no_flag_selected or category_not_selected

    @property
    def selected_flag(self) -> QcFlag | None:
        flag_index = self._qc_buttons.active
        return None if flag_index is None else self.AVAILABLE_FLAGS[flag_index]

    @property
    def layout(self):
        return self._dialog
