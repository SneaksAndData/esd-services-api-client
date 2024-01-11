from abc import ABC, abstractmethod

from adapta.metrics import MetricsProvider

from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory


class NexusObject(ABC):
    def __init__(
        self,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        self._metrics_provider = metrics_provider
        self._logger = logger_factory.create_logger(logger_type=self.__class__)

    async def __aenter__(self):
        self._logger.start()
        await self._context_open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._logger.stop()
        await self._context_close()

    @abstractmethod
    async def _context_open(self):
        """
        Optional actions to perform on context activation.
        """

    @abstractmethod
    async def _context_close(self):
        """
        Optional actions to perform on context closure.
        """
