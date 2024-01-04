import asyncio
import builtins
import os
import platform
import signal
import sys
import traceback
from functools import partial
from pydoc import locate

import backoff
import urllib3.exceptions
import azure.core.exceptions
from adapta.process_communication import DataSocket
from adapta.storage.blob.base import StorageClient
from adapta.storage.models.format import DataFrameJsonSerializationFormat
from injector import Injector

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
    INJECTION_BINDS,
)
from pandas import DataFrame as PandasDataFrame


async def main(args: CrystalEntrypointArguments):
    injector = Injector(INJECTION_BINDS)
    algorithm_class = locate(os.getenv("NEXUS__ALGORITHM_CLASS"))

    algorithm: BaselineAlgorithm = injector.get(algorithm_class)
    crystal_receiver: CrystalConnector = injector.get(CrystalConnector)
    storage_client: StorageClient = injector.get(StorageClient)

    # TODO: this should be moved to a class to allow adding callbacks via builder pattern

    algorithm_run_task = asyncio.create_task(algorithm.run(**args.__dict__))
    algorithm_run_task.add_done_callback(
        partial(submit_result, args.request_id, crystal_receiver, storage_client)
    )

    await algorithm_run_task

    ex = algorithm_run_task.exception()

    if not is_transient_exception(ex):
        crystal_receiver.submit_result(
            result=AlgorithmRunResult(
                message=f"{type(ex)}: {ex})", cause=traceback.format_exc()
            ),
            run_id=args.request_id,
            algorithm=os.getenv("CRYSTAL__ALGORITHM_NAME"),
            debug=os.getenv("IS_LOCAL_RUN") == "1",
        )
        sys.exit(0)
    else:
        sys.exit(1)


def submit_result(
    request_id: str,
    receiver: CrystalConnector,
    storage_client: StorageClient,
    completed_task: asyncio.Task,
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
        output_path = f"{os.getenv('NEXUS__ALGORITHM_OUTPUT_PATH')}/{request_id}.json"
        blob_path = DataSocket(
            data_path=output_path, alias="output", data_format=""
        ).parse_data_path()
        storage_client.save_data_as_blob(
            data=data,
            blob_path=blob_path,
            serialization_format=DataFrameJsonSerializationFormat,
            overwrite=True,
        )
        return storage_client.get_blob_uri(blob_path=blob_path)

    if not completed_task.done():
        raise RuntimeError("Attempted to submit result for an unfinished task")

    if not completed_task.exception():
        receiver.submit_result(
            result=AlgorithmRunResult(sas_uri=save_result(completed_task.result())),
            run_id=request_id,
            algorithm=os.getenv("CRYSTAL__ALGORITHM_NAME"),
            debug=os.getenv("IS_LOCAL_RUN") == "1",
        )


def is_transient_exception(exception: BaseException) -> bool:
    match type(exception):
        case azure.core.exceptions.HttpResponseError:
            return True
        case builtins.RuntimeError:
            return False
        case _:
            return False


async def graceful_shutdown():
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()

    asyncio.get_event_loop().stop()


if __name__ == "__main__":
    parser = add_crystal_args()
    if platform.system() != "Windows":
        asyncio.get_event_loop().add_signal_handler(
            signal.SIGTERM, lambda: asyncio.create_task(graceful_shutdown())
        )
        asyncio.get_event_loop().add_signal_handler(
            signal.SIGKILL, lambda: asyncio.create_task(graceful_shutdown())
        )

    asyncio.run(main(extract_crystal_args(parser.parse_args())))
