from abc import ABC, abstractmethod

from adapta.logs import create_async_logger
from adapta.logs.handlers.datadog_api_handler import DataDogApiHandler
from adapta.metrics import MetricsProvider
from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.input.input_processor import InputProcessor


class BaselineAlgorithm(ABC):
    @inject
    def __init__(
        self, input_processor: InputProcessor, metrics_provider: MetricsProvider
    ):
        self._input_processor = input_processor
        self._metrics_provider = metrics_provider
        self._logger = create_async_logger(logger_type=self.__class__, log_handlers=[])

    @abstractmethod
    async def _run(self, **kwargs) -> PandasDataFrame:
        """ """

    async def run(self, **kwargs) -> PandasDataFrame:
        return await self._run(**(await self._input_processor.process_input(**kwargs)))
