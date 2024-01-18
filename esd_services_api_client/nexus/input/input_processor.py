"""
 Input processing.
"""

#  Copyright (c) 2023. ECCO Sneaks & Data
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import asyncio
from abc import abstractmethod
from typing import Dict, Union, Type

import deltalake
from adapta.metrics import MetricsProvider

import azure.core.exceptions

from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.abstractions.nexus_object import (
    NexusObject,
    TPayload,
)
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.exceptions.input_reader_error import (
    FatalInputReaderError,
    TransientInputReaderError,
)
from esd_services_api_client.nexus.input.input_reader import InputReader


class InputProcessor(NexusObject[TPayload]):
    """
    Base class for raw data processing into algorithm input.
    """

    def __init__(
        self,
        *readers: InputReader,
        payload: TPayload,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        super().__init__(metrics_provider, logger_factory)
        self._readers = readers
        self._payload = payload

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
                return await instance.read()

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
