"""
 Metrics provider factory.
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
from typing import final

from adapta.metrics import MetricsProvider
from adapta.metrics.providers.datadog_provider import DatadogMetricsProvider


@final
class MetricsProviderFactory:
    """
    Async logger provisioner.
    """

    def __init__(
        self,
        global_tags: dict[str, str] | None = None,
    ):
        self._global_tags = global_tags
        self._metrics_class: type[MetricsProvider] = locate(
            os.getenv(
                "NEXUS__METRICS_PROVIDER_CLASS",
                "adapta.metrics.providers.datadog_provider.DatadogMetricsProvider",
            )
        )
        self._metrics_settings: dict = json.loads(
            os.getenv("NEXUS__METRICS_PROVIDER_CONFIGURATION")
        )

    def create_provider(
        self,
    ) -> MetricsProvider:
        """
        Creates a metrics provider enriched with additional tags for each metric emitted by this algorithm.
        In case of DatadogMetricsProvider, takes care of UDP/UDS specific initialization.
        """
        self._metrics_settings["fixed_tags"] = (
            self._metrics_settings.get("fixed_tags", {}) | self._global_tags
        )

        if type(self._metrics_class) is DatadogMetricsProvider:
            assert isinstance(self._metrics_class, DatadogMetricsProvider)

            if self._metrics_settings["protocol"] == "udp":
                return self._metrics_class.udp(**self._metrics_settings)

            if self._metrics_settings["protocol"] == "uds":
                return self._metrics_class.uds(**self._metrics_settings)

        return self._metrics_class(**self._metrics_settings)
