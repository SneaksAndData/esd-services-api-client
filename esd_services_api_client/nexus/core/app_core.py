"""
 Nexus Core.
"""

#  Copyright (c) 2023-2024. ECCO Sneaks & Data
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
import os
import platform
import signal
import sys
import traceback
from typing import final, Type, Optional, Coroutine

import backoff
import urllib3.exceptions
import azure.core.exceptions
from adapta.process_communication import DataSocket
from adapta.storage.blob.base import StorageClient
from adapta.storage.models.format import DataFrameJsonSerializationFormat
from injector import Injector

import esd_services_api_client.nexus.exceptions
from esd_services_api_client.crystal import (
    add_crystal_args,
    extract_crystal_args,
    CrystalConnector,
    AlgorithmRunResult,
    CrystalEntrypointArguments,
)
from esd_services_api_client.nexus.abstractions.nexus_object import AlgorithmResult
from esd_services_api_client.nexus.algorithms import (
    BaselineAlgorithm,
)
from esd_services_api_client.nexus.configurations.algorithm_configuration import (
    NexusConfiguration,
)
from esd_services_api_client.nexus.core.app_dependencies import (
    ServiceConfigurator,
)
from esd_services_api_client.nexus.input.input_processor import InputProcessor
from esd_services_api_client.nexus.input.input_reader import InputReader
from esd_services_api_client.nexus.input.payload_reader import (
    AlgorithmPayloadReader,
    AlgorithmPayload,
)


def is_transient_exception(exception: Optional[BaseException]) -> Optional[bool]:
    """
    Check if the exception is retryable.
    """
    if not exception:
        return None
    match type(exception):
        case esd_services_api_client.nexus.exceptions.FatalNexusError:
            return False
        case esd_services_api_client.nexus.exceptions.TransientNexusError:
            return True
        case _:
            return False


async def graceful_shutdown():
    """
    Gracefully stops the event loop.
    """
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()

    asyncio.get_event_loop().stop()


def attach_signal_handlers():
    """
    Signal handlers for the event loop graceful shutdown.
    """
    if platform.system() != "Windows":
        asyncio.get_event_loop().add_signal_handler(
            signal.SIGTERM, lambda: asyncio.create_task(graceful_shutdown())
        )


@final
class Nexus:
    """
    Nexus is the object that manages everything related to running algorithms through Crystal.
    It takes care of result submission, signal handling, result recording, post-processing, metrics, logging etc.
    """

    def __init__(self, args: CrystalEntrypointArguments):
        self._configurator = ServiceConfigurator()
        self._injector: Optional[Injector] = None
        self._algorithm_class: Optional[Type[BaselineAlgorithm]] = None
        self._run_args = args
        self._algorithm_run_task: Optional[asyncio.Task] = None
        self._on_complete_tasks: list[Coroutine] = []

        attach_signal_handlers()

    @property
    def algorithm_class(self) -> Type[BaselineAlgorithm]:
        """
        Class of the algorithm used by this Nexus instance.
        """
        return self._algorithm_class

    def on_complete(self, coro: Coroutine) -> "Nexus":
        """
        Attaches a coroutine to run on algorithm completion.
        """
        self._on_complete_tasks.append(coro)
        return self

    def add_reader(self, reader: Type[InputReader]) -> "Nexus":
        """
        Adds an input data reader for the algorithm.
        """
        self._configurator = self._configurator.with_input_reader(reader)
        return self

    def use_processor(self, input_processor: Type[InputProcessor]) -> "Nexus":
        """
        Initialises an input processor for the algorithm.
        """
        self._configurator = self._configurator.with_input_processor(input_processor)
        return self

    def use_algorithm(self, algorithm: Type[BaselineAlgorithm]) -> "Nexus":
        """
        Algorithm to use for this Nexus instance
        """
        self._algorithm_class = algorithm
        return self

    async def inject_payload(self, *payload_types: Type[AlgorithmPayload]) -> "Nexus":
        """
        Adds payloads processed into the specified types to the DI container
        """
        for payload_type in payload_types:

            async def get_payload() -> payload_type:  # pylint: disable=W0640
                async with AlgorithmPayloadReader(
                    payload_uri=self._run_args.sas_uri,
                    payload_type=payload_type,  # pylint: disable=W0640
                ) as reader:
                    return reader.payload

            # pylint warnings are silenced here because closure is called inside the same loop it is defined, thus each value of a loop variable is used

            self._configurator = self._configurator.with_payload((await get_payload()))
        return self

    def inject_configuration(
        self, *configuration_types: Type[NexusConfiguration]
    ) -> "Nexus":
        """
        Adds custom configuration class instances to the DI container.
        """
        for config_type in configuration_types:
            self._configurator = self._configurator.with_configuration(
                config_type.from_environment()
            )

        return self

    async def _submit_result(
        self,
        result: Optional[AlgorithmResult] = None,
        ex: Optional[BaseException] = None,
    ) -> None:
        @backoff.on_exception(
            wait_gen=backoff.expo,
            exception=(
                azure.core.exceptions.HttpResponseError,
                urllib3.exceptions.HTTPError,
            ),
            max_time=10,
            raise_on_giveup=True,
        )
        def save_result(data: AlgorithmResult) -> str:
            """
            Saves blob and returns the uri

            :param: path: path to save the blob
            :param: output_consumer_df: Formatted dataframe into ECCO format
            :param: storage_client: Azure storage client

            :return: blob uri
            """
            storage_client = self._injector.get(StorageClient)
            output_path = f"{os.getenv('NEXUS__ALGORITHM_OUTPUT_PATH')}/{self._run_args.request_id}.json"
            blob_path = DataSocket(
                data_path=output_path, alias="output", data_format="null"
            ).parse_data_path()
            storage_client.save_data_as_blob(
                data=data.dataframe(),
                blob_path=blob_path,
                serialization_format=DataFrameJsonSerializationFormat,
                overwrite=True,
            )
            return storage_client.get_blob_uri(blob_path=blob_path)

        receiver = self._injector.get(CrystalConnector)

        match is_transient_exception(ex):
            case None:
                receiver.submit_result(
                    result=AlgorithmRunResult(sas_uri=save_result(result)),
                    run_id=self._run_args.request_id,
                    algorithm=os.getenv("CRYSTAL__ALGORITHM_NAME"),
                    debug=os.getenv("IS_LOCAL_RUN") == "1",
                )
            case True:
                sys.exit(1)
            case False:
                receiver.submit_result(
                    result=AlgorithmRunResult(
                        message=f"{type(ex)}: {ex})", cause=traceback.format_exc()
                    ),
                    run_id=self._run_args.request_id,
                    algorithm=os.getenv("CRYSTAL__ALGORITHM_NAME"),
                    debug=os.getenv("IS_LOCAL_RUN") == "1",
                )
            case _:
                sys.exit(1)

    async def activate(self):
        """
        Activates the run sequence.
        """
        self._injector = Injector(self._configurator.injection_binds)

        algorithm: BaselineAlgorithm = self._injector.get(self._algorithm_class)

        async with algorithm as instance:
            self._algorithm_run_task = asyncio.create_task(
                instance.run(**self._run_args.__dict__)
            )
            await self._algorithm_run_task
            ex = self._algorithm_run_task.exception()
            on_complete_tasks = [
                asyncio.create_task(on_complete_task)
                for on_complete_task in self._on_complete_tasks
            ]

            await self._submit_result(
                self._algorithm_run_task.result() if not ex else None,
                self._algorithm_run_task.exception(),
            )
            if len(on_complete_tasks) > 0:
                await asyncio.wait(on_complete_tasks)

    @classmethod
    def create(cls) -> "Nexus":
        """
        Creates a Nexus instance with Crystal CLI arguments parsed into input.
        """
        parser = add_crystal_args()
        return Nexus(extract_crystal_args(parser.parse_args()))
