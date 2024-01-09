from typing import Type

from esd_services_api_client.nexus.exceptions._nexus_error import (
    FatalNexusError,
    TransientNexusError,
)


class FatalInputReaderError(FatalNexusError):
    def __init__(self, failed_reader: str, underlying: BaseException):
        super().__init__()
        self.with_traceback(underlying.__traceback__)
        self._failed_reader = failed_reader

    def __str__(self) -> str:
        return f"Reader for alias '{self._failed_reader}' failed to fetch the data and this operation cannot be retried. Review traceback for more information"


class TransientInputReaderError(TransientNexusError):
    def __init__(self, failed_reader: str, underlying: BaseException):
        super().__init__()
        self.with_traceback(underlying.__traceback__)
        self._failed_reader = failed_reader

    def __str__(self) -> str:
        return f"Reader for alias '{self._failed_reader}' failed to fetch the data. This error can be resolved by retrying the operation"
