"""
 Dependency injections.
"""

#  Copyright (c) 2023-2024. ECCO Sneaks & Data
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import json
import os
from pydoc import locate
from typing import final, Type

from adapta.metrics import MetricsProvider
from adapta.storage.blob.base import StorageClient
from adapta.storage.query_enabled_store import QueryEnabledStore
from injector import Module, singleton, provider

from esd_services_api_client.crystal import CrystalConnector
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.abstractions.socket_provider import (
    ExternalSocketProvider,
)
from esd_services_api_client.nexus.configurations.algorithm_configuration import (
    NexusConfiguration,
)
from esd_services_api_client.nexus.exceptions.startup_error import (
    FatalStartupConfigurationError,
)
from esd_services_api_client.nexus.input.input_processor import InputProcessor
from esd_services_api_client.nexus.input.input_reader import InputReader
from esd_services_api_client.nexus.input.payload_reader import (
    AlgorithmPayload,
)


@final
class MetricsModule(Module):
    """
    Metrics provider module.
    """

    @singleton
    @provider
    def provide(self) -> MetricsProvider:
        """
        DI factory method.
        """
        metrics_class: Type[MetricsProvider] = locate(
            os.getenv(
                "NEXUS__METRIC_PROVIDER_CLASS",
                "adapta.metrics.providers.datadog_provider.DatadogMetricsProvider",
            )
        )
        metrics_settings = json.loads(os.getenv("NEXUS__METRIC_PROVIDER_CONFIGURATION"))
        return metrics_class(**metrics_settings)


@final
class LoggerFactoryModule(Module):
    """
    Logger factory module.
    """

    @singleton
    @provider
    def provide(self) -> LoggerFactory:
        """
        DI factory method.
        """
        return LoggerFactory()


@final
class CrystalReceiverClientModule(Module):
    """
    Crystal receiver module.
    """

    @singleton
    @provider
    def provide(self) -> CrystalConnector:
        """
        DI factory method.
        """
        return CrystalConnector.create_anonymous(
            receiver_base_url=os.getenv("NEXUS__CRYSTAL_RECEIVER_URL"),
        )


@final
class QueryEnabledStoreModule(Module):
    """
    QES module.
    """

    @singleton
    @provider
    def provide(self) -> QueryEnabledStore:
        """
        DI factory method.
        """
        return QueryEnabledStore.from_string(os.getenv("NEXUS__QES_CONNECTION_STRING"))


@final
class StorageClientModule(Module):
    """
    Storage client module.
    """

    @singleton
    @provider
    def provide(self) -> StorageClient:
        """
        DI factory method.
        """
        storage_client_class: Type[StorageClient] = locate(
            os.getenv(
                "NEXUS__STORAGE_CLIENT_CLASS",
            )
        )
        if not storage_client_class:
            raise FatalStartupConfigurationError("NEXUS__STORAGE_CLIENT_CLASS")
        if "NEXUS__ALGORITHM_OUTPUT_PATH" not in os.environ:
            raise FatalStartupConfigurationError("NEXUS__ALGORITHM_OUTPUT_PATH")

        return storage_client_class.for_storage_path(
            path=os.getenv("NEXUS__ALGORITHM_OUTPUT_PATH")
        )


@final
class ExternalSocketsModule(Module):
    """
    Storage client module.
    """

    @singleton
    @provider
    def provide(self) -> ExternalSocketProvider:
        """
        Dependency provider.
        """
        if "NEXUS__ALGORITHM_INPUT_EXTERNAL_DATA_SOCKETS" not in os.environ:
            raise FatalStartupConfigurationError(
                "NEXUS__ALGORITHM_INPUT_EXTERNAL_DATA_SOCKETS"
            )

        return ExternalSocketProvider.from_serialized(
            os.getenv("NEXUS__ALGORITHM_INPUT_EXTERNAL_DATA_SOCKETS")
        )


@final
class ServiceConfigurator:
    """
    Runtime DI support.
    """

    def __init__(self):
        self._injection_binds = [
            MetricsModule(),
            CrystalReceiverClientModule(),
            QueryEnabledStoreModule(),
            StorageClientModule(),
            ExternalSocketsModule(),
        ]

    @property
    def injection_binds(self) -> list:
        """
        Currently configured injection bindings
        """
        return self._injection_binds

    def with_input_reader(self, reader: Type[InputReader]) -> "ServiceConfigurator":
        """
        Adds the input reader implementation to the DI.
        """
        self._injection_binds.append(type(f"{reader.__name__}Module", (Module,), {})())
        return self

    def with_input_processor(
        self, input_processor: Type[InputProcessor]
    ) -> "ServiceConfigurator":
        """
        Adds the input processor implementation
        """
        self._injection_binds.append(
            type(f"{input_processor.__name__}Module", (Module,), {})()
        )
        return self

    def with_payload(self, payload: AlgorithmPayload) -> "ServiceConfigurator":
        """
        Adds the specified payload instance to the DI container.
        """
        self._injection_binds.append(
            lambda binder: binder.bind(payload.__class__, to=payload, scope=singleton)
        )
        return self

    def with_configuration(self, config: NexusConfiguration) -> "ServiceConfigurator":
        """
        Adds the specified payload instance to the DI container.
        """
        self._injection_binds.append(
            lambda binder: binder.bind(config.__class__, to=config, scope=singleton)
        )
        return self
