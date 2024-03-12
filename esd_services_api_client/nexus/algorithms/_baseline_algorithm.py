"""
 Base algorithm
"""
import asyncio

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


from abc import abstractmethod
from functools import reduce

from adapta.metrics import MetricsProvider

from esd_services_api_client.nexus.abstractions.nexus_object import (
    NexusObject,
    TPayload,
    AlgorithmResult,
)
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.input.input_processor import (
    InputProcessor,
    resolve_processors,
)


class BaselineAlgorithm(NexusObject[TPayload, AlgorithmResult]):
    """
    Base class for all algorithm implementations.
    """

    def __init__(
        self,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        *input_processors: InputProcessor,
    ):
        super().__init__(metrics_provider, logger_factory)
        self._input_processors = input_processors

    @abstractmethod
    async def _run(self, **kwargs) -> AlgorithmResult:
        """
        Core logic for this algorithm. Implementing this method is mandatory.
        """

    async def run(self, **kwargs) -> AlgorithmResult:
        """
        Coroutine that executes the algorithm logic.
        """

        results = await resolve_processors(*self._input_processors, **kwargs)

        return await self._run(
            **reduce(lambda a, b: a | b, [result for _, result in results.items()])
        )
