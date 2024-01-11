import json
import os
from logging import StreamHandler
from pydoc import locate
from typing import final, Type, TypeVar, Optional, Dict

from adapta.logs import create_async_logger
from adapta.logs._async_logger import _AsyncLogger
from adapta.logs.handlers.datadog_api_handler import DataDogApiHandler
from adapta.logs.models import LogLevel
from adapta.metrics import MetricsProvider
from adapta.storage.blob.base import StorageClient
from adapta.storage.query_enabled_store import QueryEnabledStore
from injector import Module, singleton, provider, Binder

from esd_services_api_client.crystal import CrystalConnector
from esd_services_api_client.nexus.exceptions.startup_error import (
    FatalStartupConfigurationError,
)
from esd_services_api_client.nexus.input.input_processor import InputProcessor
from esd_services_api_client.nexus.input.input_reader import InputReader

TLogger = TypeVar("TLogger")


@final
class LoggerFactory:
    def __init__(self):
        self._log_handlers = [
            StreamHandler(),
        ]
        if "NEXUS__DATADOG_LOGGER_CONFIGURATION" in os.environ:
            self._log_handlers.append(
                DataDogApiHandler(
                    **json.loads(os.getenv("NEXUS__DATADOG_LOGGER_CONFIGURATION"))
                )
            )

    def create_logger(
        self,
        logger_type: Type[TLogger],
        fixed_template: Optional[Dict[str, Dict[str, str]]] = None,
        fixed_template_delimiter=", ",
    ) -> _AsyncLogger[TLogger]:
        return create_async_logger(
            logger_type=logger_type,
            log_handlers=self._log_handlers,
            min_log_level=LogLevel(os.getenv("NEXUS__LOG_LEVEL", "INFO")),
            fixed_template=fixed_template,
            fixed_template_delimiter=fixed_template_delimiter,
        )


class MetricsModule(Module):
    @singleton
    @provider
    def provide(self) -> MetricsProvider:
        metrics_class: Type[MetricsProvider] = locate(
            os.getenv(
                "NEXUS__METRIC_PROVIDER_CLASS",
                "adapta.metrics.providers.datadog_provider.DatadogMetricsProvider",
            )
        )
        metrics_settings = json.loads(os.getenv("NEXUS__METRIC_PROVIDER_CONFIGURATION"))
        return metrics_class(**metrics_settings)


class LoggerFactoryModule(Module):
    @singleton
    @provider
    def provide(self) -> LoggerFactory:
        return LoggerFactory()


class CrystalReceiverClientModule(Module):
    @singleton
    @provider
    def provide(self) -> CrystalConnector:
        return CrystalConnector.create_anonymous(
            receiver_base_url=os.getenv("NEXUS__ALGORITHM_METRIC_NAMESPACE"),
            logger=create_async_logger(
                logger_type=CrystalConnector, log_handlers=[StreamHandler()]
            ),
        )


class QueryEnabledStoreModule(Module):
    @singleton
    @provider
    def provide_qes(self) -> QueryEnabledStore:
        return QueryEnabledStore.from_string(os.getenv("NEXUS__QES_CONNECTION_STRING"))


class StorageClientModule(Module):
    @singleton
    @provider
    def provide(self) -> StorageClient:
        storage_client_class: Type[StorageClient] = locate(
            os.getenv(
                "NEXUS__STORAGE_CLIENT_CLASS",
            )
        )
        if not storage_client_class:
            raise FatalStartupConfigurationError("NEXUS__STORAGE_CLIENT_CLASS")
        if not "NEXUS__ALGORITHM_OUTPUT_PATH" not in os.environ:
            raise FatalStartupConfigurationError("NEXUS__ALGORITHM_OUTPUT_PATH")

        return storage_client_class.for_storage_path(
            path=os.getenv("NEXUS__ALGORITHM_OUTPUT_PATH")
        )


def binds(binder: Binder):
    pass


@final
class ServiceConfigurator:
    def __init__(self):
        self._injection_binds = [
            binds,
            MetricsModule(),
            CrystalReceiverClientModule(),
            QueryEnabledStoreModule(),
            StorageClientModule(),
        ]

    @property
    def injection_binds(self) -> list:
        return self._injection_binds

    def with_input_reader(self, reader: Type[InputReader]) -> "ServiceConfigurator":
        self._injection_binds.append(type(f"{reader.__name__}Module", (Module,), {})())
        return self

    def with_input_processor(
        self, input_processor: Type[InputProcessor]
    ) -> "ServiceConfigurator":
        self._injection_binds.append(
            type(f"{input_processor.__name__}Module", (Module,), {})()
        )
        return self
