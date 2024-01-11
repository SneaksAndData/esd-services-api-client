from abc import abstractmethod

from adapta.metrics import MetricsProvider
from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.abstractions.nexus_object import NexusObject
from esd_services_api_client.nexus.core.app_dependencies import LoggerFactory
from esd_services_api_client.nexus.input.input_processor import InputProcessor


class BaselineAlgorithm(NexusObject):
    @inject
    def __init__(
        self,
        input_processor: InputProcessor,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        super().__init__(metrics_provider, logger_factory)
        self._input_processor = input_processor

    @abstractmethod
    async def _run(self, **kwargs) -> PandasDataFrame:
        """
        Core logic for this algorithm. Implementing this method is mandatory.
        """

    async def run(self, **kwargs) -> PandasDataFrame:
        """
        Coroutine that executes the algorithm logic.
        """
        with self._input_processor as input_processor:
            return await self._run(**(await input_processor.process_input(**kwargs)))
