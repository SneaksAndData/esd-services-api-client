import re
from abc import ABC, abstractmethod
from functools import partial
from typing import Optional

from adapta.metrics import MetricsProvider
from adapta.process_communication import DataSocket
from adapta.storage.query_enabled_store import QueryEnabledStore
from pandas import DataFrame as PandasDataFrame
from adapta.utils.decorators import run_time_metrics

from esd_services_api_client.nexus.abstractions.nexus_object import NexusObject
from esd_services_api_client.nexus.core.app_dependencies import LoggerFactory


class InputReader(NexusObject):
    def __init__(
        self,
        socket: DataSocket,
        store: QueryEnabledStore,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        *readers: "InputReader"
    ):
        super().__init__(metrics_provider, logger_factory)
        self.socket = socket
        self._store = store
        self._data: Optional[PandasDataFrame] = None
        self._readers = readers

    @property
    def data(self) -> Optional[PandasDataFrame]:
        return self._data

    @abstractmethod
    async def _read_input(self) -> PandasDataFrame:
        """
        Actual data reader logic. Implementing this method is mandatory for the reader to work
        """

    @property
    def _metric_name(self) -> str:
        return re.sub(
            r"(?<!^)(?=[A-Z])",
            "_",
            self.__class__.__name__.lower().replace("reader", ""),
        )

    @property
    def _metric_tags(self) -> dict[str, str]:
        return {"entity": self._metric_name}

    async def read(self) -> PandasDataFrame:
        """
        Coroutine that reads the data from external store and converts it to a dataframe.
        """

        @run_time_metrics(metric_name="read_input")
        async def _read(**_) -> PandasDataFrame:
            if not self._data:
                self._data = await self._read_input()

            return self._data

        return await partial(
            _read,
            metric_tags=self._metric_tags,
            metrics_provider=self._metrics_provider,
            logger=self._logger,
        )()
