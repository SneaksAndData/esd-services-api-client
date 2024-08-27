import os.path
import re
from abc import ABC, abstractmethod
from functools import partial

from adapta.process_communication import DataSocket
from adapta.storage.blob.base import StorageClient
from pandas import DataFrame

from adapta.logs import LoggerInterface
from adapta.metrics import MetricsProvider
from adapta.utils.decorators import run_time_metrics_async
from dataclasses_json.stringcase import snakecase
from injector import inject

from esd_services_api_client.nexus.abstractions.nexus_object import AlgorithmResult
from esd_services_api_client.nexus.core.serializers import TelemetrySerializer
from esd_services_api_client.nexus.input.payload_reader import AlgorithmPayload


class UserTelemetryRecorder(ABC):
    @inject
    def __init__(
        self,
        algorithm_payload: AlgorithmPayload,
        metrics_provider: MetricsProvider,
        logger: LoggerInterface,
        storage_client: StorageClient,
        serializer: TelemetrySerializer,
        telemetry_base_path: str,
    ):
        self._metrics_provider = metrics_provider
        self._logger = logger
        self._payload = algorithm_payload
        self._storage_client = storage_client
        self._serializer = serializer
        self._telemetry_base_path = telemetry_base_path

    @property
    def _metric_tags(self) -> dict[str, str]:
        return {"recorder": self.__class__.alias().upper()}

    @abstractmethod
    async def _compute(
        self,
        algorithm_payload: AlgorithmPayload,
        algorithm_result: AlgorithmResult,
        run_id: str,
        **inputs: DataFrame,
    ) -> DataFrame:
        """
        Produces the dataframe to record as user-level telemetry data.
        """

    async def record(
        self, algorithm_result: AlgorithmResult, run_id: str, **inputs: DataFrame
    ):
        @run_time_metrics_async(
            metric_name="user_telemetry_recording",
            on_finish_message_template="Finished recording telemetry from {recorder} in {elapsed:.2f}s seconds",
            template_args={
                "recorder": self.__class__.alias().upper(),
            },
        )
        async def _measured_recording(**run_args):
            return await self._compute(**run_args)

        telemetry = await partial(
            _measured_recording,
            **(
                {
                    "algorithm_payload": self._payload,
                    "algorithm_result": algorithm_result,
                    "run_id": run_id,
                }
                | inputs
            ),
            metric_tags=self._metric_tags,
            metrics_provider=self._metrics_provider,
            logger=self._logger,
        )()

        self._storage_client.save_data_as_blob(
            data=telemetry,
            blob_path=DataSocket(
                alias="user_telemetry",
                data_path=os.path.join(
                    self._telemetry_base_path,
                    "telemetry_group=user",
                    f"recorder_class={self.__class__.alias()}",
                    f"request_id={run_id}",
                ),
                data_format="null",
            ).parse_data_path(),
            serialization_format=self._serializer.get_serialization_format(telemetry),
            overwrite=True,
        )

    @classmethod
    def alias(cls) -> str:
        """
        Alias to identify this recorder in logging and metrics data.
        """
        return snakecase(
            re.sub(
                r"(?<!^)(?=[A-Z])",
                "_",
                cls.__name__.lower(),
            )
        )
