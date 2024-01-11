from esd_services_api_client.nexus.exceptions import FatalNexusError


class FatalServiceStartupError(FatalNexusError):
    def __init__(self, service: str, underlying: BaseException):
        super().__init__()
        self.with_traceback(underlying.__traceback__)
        self._service = service

    def __str__(self) -> str:
        return f"Algorithm initialization failed on service {self._service} startup. Review the traceback for more information"


class FatalStartupConfigurationError(FatalNexusError):
    def __init__(self, missing_entry: str):
        super().__init__()
        self._missing_entry = missing_entry

    def __str__(self) -> str:
        return f"Algorithm initialization failed due to a missing configuration entry: {self._missing_entry}."
