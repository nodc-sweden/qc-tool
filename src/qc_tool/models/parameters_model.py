from qc_tool.models.base_model import BaseModel


class ParametersModel(BaseModel):
    NEW_PARAMETERS = "NEW_PARAMETERS"
    NEW_SELECTION = "NEW_SELECTION"
    NEW_PARAMETER_DATA = "NEW_PARAMETER_DATA"

    _multi_parameters = (
        ("SALT_CTD", "SALT_BTL"),
        ("TEMP_CTD", "TEMP_BTL"),
        ("SALT_CTD", "TEMP_CTD"),
        ("DOXY_CTD", "DOXY_BTL"),
        ("DOXY_CTD", "DOXY_BTL", "H2S"),
        ("AMON", "NTRA", "NTRI"),
        ("AMON", "NTRZ", "NTRI"),
        ("PTOT", "PHOS", "SIO3-SI"),
        ("PTOT", "PHOS"),
        ("NTOT", "NTRA", "AMON"),
        ("NTOT", "NTRZ", "AMON"),
        ("PHOS", "AMON", "DOXY_BTL"),
        ("ALK", "PH-TOT"),
        ("CPHL", "CHLFL", "DOXY_BTL"),
        ("CHLFL", "DOXY_CTD"),
        ("CPHL", "CHLFL"),
    )

    _default_parameters = DEFAULT_PARAMETERS = (
        "SALT_CTD + SALT_BTL",
        "TEMP_CTD + TEMP_BTL",
        "DOXY_CTD + DOXY_BTL",
        "NTOT + NTRZ + AMON",
        "PTOT + PHOS + SIO3-SI",
        "ALK + PH-TOT",
        "CPHL + CHLFL",
        "DOXY_CTD + DOXY_BTL + H2S",
        "AMON",
        "PHOS",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._available_parameters = set()
        self._available_multi_parameters = set()
        self._selected_parameters = []
        self._parameter_data = {}

    @property
    def available_parameters(self):
        return sorted(self._available_parameters - set(self._selected_parameters))

    @property
    def available_multiparameters(self):
        return sorted(self._available_multi_parameters - set(self._selected_parameters))

    @available_parameters.setter
    def available_parameters(self, available_parameters: list[str]):
        self._available_parameters = set(available_parameters)
        self._available_multi_parameters = set()
        for parameters in self._multi_parameters:
            if set(parameters).issubset(self._available_parameters):
                self._available_multi_parameters.add(" + ".join(parameters))
        self._notify_listeners(self.NEW_PARAMETERS)

    @property
    def selection_size(self):
        return len(self._selected_parameters)

    @property
    def selected_parameters(
        self,
    ):
        return self._selected_parameters

    @selected_parameters.setter
    def selected_parameters(self, selected_parameters: list[str]):
        if selected_parameters != self._selected_parameters:
            self._selected_parameters = selected_parameters
            self._notify_listeners(self.NEW_SELECTION)

    @property
    def parameter_data(self):
        return self._parameter_data

    @property
    def enabled(self) -> bool:
        return len(self._available_parameters) > 0

    # TODO: kolla att man inte valt för många

    def set_default_parameters(self):
        self.selected_parameters = list(self._default_parameters)

    def reset_parameter_data(self):
        self._parameter_data = {}
        self._notify_listeners(self.NEW_PARAMETER_DATA)
