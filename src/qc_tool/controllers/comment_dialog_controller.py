from ocean_data_qc.fyskem.qc_flag import QcFlag

from qc_tool.models.manual_qc_model import ManualQcModel
from qc_tool.views.comment_dialog_view import CommentDialogView


class CommentDialogController:
    NO_COMMENT = "No comment"

    COMMENT_CATEGORIES = (
        (NO_COMMENT, {}),
        ("Svavelväte förekommer", {QcFlag.BAD_VALUE}),
        ("Värde avviker i homogent lager", {QcFlag.BAD_VALUE, QcFlag.PROBABLY_BAD_VALUE}),
        ("Kontrollera för stansfel", {QcFlag.PROBABLY_BAD_VALUE}),
        ("Totalhalt avvikande högt/lågt värde", {QcFlag.PROBABLY_BAD_VALUE}),
        ("Provtaget i gränsskikt", {QcFlag.BAD_VALUE, QcFlag.PROBABLY_BAD_VALUE}),
        (
            "CTD och flaska stämmer ej",
            {QcFlag.BAD_VALUE, QcFlag.PROBABLY_BAD_VALUE},
        ),
        ("Analysen misslyckades", {QcFlag.BAD_VALUE}),
        ("Provtagning misslyckades", {QcFlag.BAD_VALUE}),
        ("Flaska stängt på fel djup", {QcFlag.BAD_VALUE}),
        ("Förväxlade djup", {QcFlag.BAD_VALUE}),
        ("Auto qc fel", {}),
        ("Annat/fritext", {}),
    )

    def __init__(self, manual_qc: ManualQcModel):
        self._manual_qc_model = manual_qc
        self._manual_qc_model.register_listener(
            ManualQcModel.FLAG_REQUESTED, self._on_flag_requested
        )
        self._comment_dialog_view: CommentDialogView | None = None

    def _on_flag_requested(self):
        if self._comment_dialog_view is None:
            return
        categories = self._categories_for_flag(self._manual_qc_model.pending_flag)
        self._comment_dialog_view.open(self._manual_qc_model.pending_flag, categories)

    def on_ok(self, category: str, comment: str):
        self._manual_qc_model.confirm_flag(category, comment.strip())
        if self._comment_dialog_view is not None:
            self._comment_dialog_view.close()

    def on_cancel(self):
        if self._comment_dialog_view is not None:
            self._comment_dialog_view.close()
        self._manual_qc_model.cancel_flag()

    @classmethod
    def _categories_for_flag(cls, flag: QcFlag) -> list[str]:
        return [
            category
            for category, flag_filter in cls.COMMENT_CATEGORIES
            if not flag_filter or flag in flag_filter
        ]
