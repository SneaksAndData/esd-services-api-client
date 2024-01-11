import asyncio
from abc import abstractmethod
from typing import Dict, Union, Type

import deltalake
from adapta.metrics import MetricsProvider

import azure.core.exceptions

from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.abstractions.nexus_object import NexusObject
from esd_services_api_client.nexus.core.app_dependencies import LoggerFactory
from esd_services_api_client.nexus.exceptions.input_reader_error import (
    FatalInputReaderError,
    TransientInputReaderError,
)
from esd_services_api_client.nexus.input.input_reader import InputReader


class InputProcessor(NexusObject):
    @inject
    def __init__(
        self,
        *readers: InputReader,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        super().__init__(metrics_provider, logger_factory)
        self._readers = readers

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

        async def _read(input_reader: InputReader):
            async with input_reader as instance:
                return instance.read()

        read_tasks: dict[str, asyncio.Task] = {
            reader.socket.alias: asyncio.create_task(_read(reader))
            for reader in self._readers
        }
        await asyncio.wait(fs=read_tasks.values())

        return {alias: get_result(alias, task) for alias, task in read_tasks.items()}

    @abstractmethod
    async def process_input(self, **kwargs) -> Dict[str, PandasDataFrame]:
        """
        Input processing logic. Implement this method to prepare data for your algorithm code.
        """
