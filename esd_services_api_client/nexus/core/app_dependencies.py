import json
import os
from typing import Dict, Optional

from adapta.metrics.providers.datadog_provider import DatadogMetricsProvider
from injector import Module, singleton, provider, Binder


class DatadogMetricsConfiguration:
    def __init__(
        self, metric_namespace: str, fixed_tags: Optional[Dict[str, str]] = None
    ):
        self.metric_namespace = metric_namespace
        self.fixed_tags = fixed_tags

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


def metrics_binder(binder: Binder):
    binder.bind(
        DatadogMetricsConfiguration,
        to=DatadogMetricsConfiguration.from_environment(),
        scope=singleton,
    )


INJECTION_BINDS = [metrics_binder, DatadogMetricsModule()]
