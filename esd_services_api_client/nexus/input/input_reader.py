import re
from abc import ABC, abstractmethod
from functools import partial
from typing import Optional

from adapta.logs import SemanticLogger
from adapta.metrics import MetricsProvider
from adapta.process_communication import DataSocket
from adapta.storage.query_enabled_store import QueryEnabledStore
from injector import inject
from pandas import DataFrame as PandasDataFrame
from adapta.utils.decorators import run_time_metrics


class InputReader(ABC):
    @inject
    def __init__(
        self,
        socket: DataSocket,
        store: QueryEnabledStore,
        metrics_provider: MetricsProvider,
        logger: SemanticLogger,
        *readers: "InputReader",
    ):
        self.socket = socket
        self._store = store
        self._metrics_provider = metrics_provider
        self._logger = logger
        self._data: Optional[PandasDataFrame] = None
        self._readers = readers

    @property
    def data(self) -> Optional[PandasDataFrame]:
        return self._data

    @abstractmethod
    async def _read_input(self) -> PandasDataFrame:
        """ """

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
        @run_time_metrics(metric_name="read_input")
        async def _read(**_) -> PandasDataFrame:
            if not self._data:
                self._data = await self._read_input()

            return self._data

        return partial(
            _read,
            metric_tags=self._metric_tags,
            metrics_provider=self._metrics_provider,
        )
