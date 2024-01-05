from abc import ABC, abstractmethod

from adapta.logs import SemanticLogger
from adapta.metrics import MetricsProvider
from adapta.process_communication import DataSocket
from adapta.storage.query_enabled_store import QueryEnabledStore
from injector import inject
from pandas import DataFrame as PandasDataFrame
from adapta.utils.decorators import run_time_metrics


class InputReader(ABC):
    # TODO: change logger type to async-compat
    @inject
    def __init__(
        self,
        socket: DataSocket,
        store: QueryEnabledStore,
        metrics_provider: MetricsProvider,
        logger: SemanticLogger,
    ):
        self.socket = socket
        self._store = store
        self._metrics_provider = metrics_provider
        self._logger = logger

    @abstractmethod
    def _read_input(self) -> PandasDataFrame:
        """ """

    async def read(self) -> PandasDataFrame:
        # TODO: add appropriate metric tags based on snake_case_class_name
        @run_time_metrics(metric_name=f"read_input")
        def _read(
            metric_tags={}, metrics_provider=self._metrics_provider
        ) -> PandasDataFrame:
            return self._read_input()

        return _read()
