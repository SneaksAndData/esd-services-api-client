import asyncio
from abc import abstractmethod, ABC
from typing import Dict, Union, Type

import deltalake
from adapta.logs import create_async_logger
from adapta.logs.handlers.datadog_api_handler import DataDogApiHandler
from adapta.metrics import MetricsProvider

import azure.core.exceptions
from adapta.metrics.providers.datadog_provider import DatadogMetricsProvider

from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.exceptions.input_reader_error import (
    FatalInputReaderError,
    TransientInputReaderError,
)
from esd_services_api_client.nexus.input.input_reader import InputReader


class InputProcessor(ABC):
    @inject
    def __init__(self, *readers: InputReader, metrics_provider: DatadogMetricsProvider): # log_handler: DataDogApiHandler
        self._readers = readers
        self._metrics_provider = metrics_provider
        # TODO: logger and handler configuration
        self._logger = create_async_logger(
            logger_type=self.__class__, log_handlers=[] # log_handler
        )

    def _get_exc_type(
        self, ex: BaseException
    ) -> Union[Type[FatalInputReaderError], Type[TransientInputReaderError]]:
        match type(ex):
            case azure.core.exceptions.HttpResponseError, deltalake.PyDeltaTableError:
                return TransientInputReaderError
            case azure.core.exceptions.AzureError, azure.core.exceptions.ClientAuthenticationError:
                return FatalInputReaderError
            case _:
                return FatalInputReaderError

    async def _read_input(self) -> Dict[str, PandasDataFrame]:
        def get_result(alias: str, completed_task: asyncio.Task) -> PandasDataFrame:
            reader_exc = completed_task.exception()
            if reader_exc:
                raise self._get_exc_type(reader_exc)(alias, reader_exc)

            return completed_task.result()

        read_tasks: dict[str, asyncio.Task] = {
            reader.socket.alias: asyncio.create_task(reader.read())
            for reader in self._readers
        }
        await asyncio.wait(fs=read_tasks.values())

        return {alias: get_result(alias, task) for alias, task in read_tasks.items()}

    @abstractmethod
    async def process_input(self, **kwargs) -> Dict[str, PandasDataFrame]:
        """ """
