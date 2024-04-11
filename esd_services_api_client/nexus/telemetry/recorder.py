"""
 Telemetry recording module.
"""
import asyncio
import os
from functools import partial
from typing import final

import pandas as pd
from adapta.metrics import MetricsProvider
from adapta.process_communication import DataSocket
from adapta.storage.blob.base import StorageClient
from adapta.storage.models.format import (
    DictJsonSerializationFormat,
    DataFrameParquetSerializationFormat,
)
from injector import inject, singleton

from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.abstractions.nexus_object import NexusCoreObject


@final
@singleton
class TelemetryRecorder(NexusCoreObject):
    """
    Class for instantiating a telemetry recorder that will save all algorithm inputs (run method arguments) to a persistent location.
    """

    async def _context_open(self):
        pass

    async def _context_close(self):
        pass

    @inject
    def __init__(
        self,
        storage_client: StorageClient,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        super().__init__(metrics_provider, logger_factory)
        self._storage_client = storage_client
        self._telemetry_base_path = os.getenv("NEXUS__TELEMETRY_PATH")

    async def record(self, run_id: str, **telemetry_args):
        """
        Record all data in telemetry args for the provided run_id.
        """

        async def _record(
            entity_to_record: pd.DataFrame | dict,
            entity_name: str,
            **_,
        ) -> None:
            self._logger.debug(
                "Recording telemetry for {entity_name} in the run {run_id}",
                entity_name=entity_name,
                run_id=run_id,
            )
            self._storage_client.save_data_as_blob(
                data=entity_to_record,
                blob_path=DataSocket(
                    alias="telemetry",
                    data_path=f"{self._telemetry_base_path}/{entity_name}/{run_id}",
                    data_format="null",
                ).parse_data_path(),
                serialization_format=DictJsonSerializationFormat
                if isinstance(entity_to_record, dict)
                else DataFrameParquetSerializationFormat,
                overwrite=True,
            )

        telemetry_tasks = [
            asyncio.create_task(
                partial(
                    _record,
                    entity_to_record=telemetry_value,
                    entity_name=telemetry_key,
                    run_id=run_id,
                )()
            )
            for telemetry_key, telemetry_value in telemetry_args.items()
        ]

        done, pending = await asyncio.wait(telemetry_tasks)
        if len(pending) > 0:
            self._logger.warning(
                "Some telemetry recording operations did not complete within specified time. This run might lack observability coverage."
            )
        for done_telemetry_task in done:
            telemetry_exc = done_telemetry_task.exception()
            if telemetry_exc:
                self._logger.warning(
                    "Telemetry recoding failed", exception=telemetry_exc
                )
