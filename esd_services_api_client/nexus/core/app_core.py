import asyncio
import builtins
import os
import platform
import signal
import sys
import traceback
from pydoc import locate
from typing import final, Type, Optional, Coroutine

import backoff
import urllib3.exceptions
import azure.core.exceptions
from adapta.process_communication import DataSocket
from adapta.storage.blob.azure_storage_client import AzureStorageClient
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
from esd_services_api_client.nexus.algorithms._baseline_algorithm import (
    BaselineAlgorithm,
)
from esd_services_api_client.nexus.core.app_dependencies import (
    ServiceConfigurator,
)
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.input.input_processor import InputProcessor
from esd_services_api_client.nexus.input.input_reader import InputReader


def is_transient_exception(exception: Optional[BaseException]) -> Optional[bool]:
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
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()

    asyncio.get_event_loop().stop()


def attach_signal_handlers():
    if platform.system() != "Windows":
        asyncio.get_event_loop().add_signal_handler(
            signal.SIGTERM, lambda: asyncio.create_task(graceful_shutdown())
        )


@final
class Nexus:
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
        return self._algorithm_class

    def on_complete(self, coro: Coroutine) -> "Nexus":
        self._on_complete_tasks.append(coro)
        return self

    def add_reader(self, reader: Type[InputReader]) -> "Nexus":
        self._configurator = self._configurator.with_input_reader(reader)
        return self

    def use_processor(self, input_processor: Type[InputProcessor]) -> "Nexus":
        self._configurator = self._configurator.with_input_processor(input_processor)
        return self

    def use_algorithm(self, algorithm: Type[BaselineAlgorithm]) -> "Nexus":
        self._algorithm_class = algorithm
        return self

    async def _submit_result(
        self,
        result: Optional[PandasDataFrame] = None,
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
        def save_result(data: PandasDataFrame) -> str:
            """
            Saves blob and returns the uri

            :param: path: path to save the blob
            :param: output_consumer_df: Formatted dataframe into ECCO format
            :param: storage_client: Azure storage client

            :return: blob uri
            """
            storage_client = self._injector.get(StorageClientFactory).get_client()
            output_path = f"{os.getenv('NEXUS__ALGORITHM_OUTPUT_PATH')}/{self._run_args.request_id}.json"
            blob_path = DataSocket(
                data_path=output_path, alias="output", data_format="null"
            ).parse_data_path()
            storage_client.save_data_as_blob(
                data=data,
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
        self._injector = Injector(self._configurator.injection_binds)
        self._algorithm_run_task = asyncio.create_task(
            self._injector.get(self._algorithm_class).run(**self._run_args.__dict__)
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
        parser = add_crystal_args()
        return Nexus(extract_crystal_args(parser.parse_args()))
