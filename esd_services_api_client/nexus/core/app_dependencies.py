import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, final, Type

from adapta.metrics.providers.datadog_provider import DatadogMetricsProvider
from injector import Module, singleton, provider, Binder

from esd_services_api_client.crystal import CrystalConnector
from esd_services_api_client.nexus.input.input_processor import InputProcessor
from esd_services_api_client.nexus.input.input_reader import InputReader


@dataclass
class DatadogMetricsConfiguration:
    metric_namespace: str
    fixed_tags: Optional[Dict[str, str]] = None

    @classmethod
    def from_environment(cls) -> "DatadogMetricsConfiguration":
        def tags_from_str(value: Optional[str]) -> Optional[Dict[str, str]]:
            if not value:
                return None

            return json.loads(value)

        return cls(
            metric_namespace=os.getenv("NEXUS__ALGORITHM_METRIC_NAMESPACE"),
            fixed_tags=tags_from_str(os.getenv("NEXUS__ALGORITHM_METRIC_TAGS")),
        )


class DatadogMetricsModule(Module):
    @singleton
    @provider
    def provide_metrics_provider(
        self, configuration: DatadogMetricsConfiguration
    ) -> DatadogMetricsProvider:
        return DatadogMetricsProvider(
            metric_namespace=configuration.metric_namespace,
            fixed_tags=configuration.fixed_tags,
        )


@dataclass
class CrystalReceiverConfiguration:
    receiver_base_url: str

    @classmethod
    def from_environment(cls) -> "CrystalReceiverConfiguration":
        return cls(
            receiver_base_url=os.getenv("NEXUS__ALGORITHM_METRIC_NAMESPACE"),
        )


class CrystalReceiverClientModule(Module):
    @singleton
    @provider
    def provide_crystal_receiver(
        self, configuration: CrystalReceiverConfiguration
    ) -> CrystalConnector:
        return CrystalConnector.create_anonymous(
            receiver_base_url=configuration.receiver_base_url
        )


def binds(binder: Binder):
    binder.bind(
        DatadogMetricsConfiguration,
        to=DatadogMetricsConfiguration.from_environment(),
        scope=singleton,
    )
    binder.bind(
        CrystalReceiverConfiguration,
        to=CrystalReceiverConfiguration.from_environment(),
        scope=singleton,
    )


@final
class ServiceConfigurator:
    def __init__(self):
        self._injection_binds = [
            binds,
            DatadogMetricsModule(),
            CrystalReceiverClientModule(),
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
