import asyncio
from abc import abstractmethod, ABC
from typing import Dict, Union, Type

import deltalake
from adapta.metrics import MetricsProvider

import azure.core.exceptions

from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.core.app_dependencies import LoggerFactory
from esd_services_api_client.nexus.exceptions.input_reader_error import (
    FatalInputReaderError,
    TransientInputReaderError,
)
from esd_services_api_client.nexus.input.input_reader import InputReader


class InputProcessor(ABC):
    @inject
    def __init__(
        self,
        *readers: InputReader,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        self._readers = readers
        self._metrics_provider = metrics_provider
        self._logger = logger_factory.create_logger(
            logger_type=self.__class__,
        )

    def __enter__(self):
        self._logger.start()
        self._context_open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger.stop()
        self._context_close()

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
    def _context_open(self):
        """
         Optional actions to perform on context activation.
        """

    @abstractmethod
    def _context_close(self):
        """
         Optional actions to perform on context closure.
        """

    @abstractmethod
    async def process_input(self, **kwargs) -> Dict[str, PandasDataFrame]:
        """
         Input processing logic. Implement this method to prepare data for your algorithm code.
        """