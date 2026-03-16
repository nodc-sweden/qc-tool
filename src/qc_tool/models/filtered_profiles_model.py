from qc_tool.models.base_model import BaseModel


class FilteredProfilesModel(BaseModel):
    NEW_SELECTION = "NEW_SELECTION"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_profile_index = None

    @property
    def selected_profile_index(self):
        return self._selected_profile_index

    @selected_profile_index.setter
    def selected_profile_index(self, selected_profile_index: int):
        self._selected_profile_index = selected_profile_index
        self._notify_listeners(self.NEW_SELECTION)
