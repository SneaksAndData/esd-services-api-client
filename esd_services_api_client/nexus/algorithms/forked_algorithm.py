"""
 Remotely executed algorithm
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

import asyncio
from abc import abstractmethod
from functools import reduce, partial

from adapta.metrics import MetricsProvider
from adapta.utils.decorators import run_time_metrics_async

from esd_services_api_client.nexus.abstractions.nexus_object import (
    NexusObject,
    TPayload,
    AlgorithmResult,
)
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.algorithms._remote_algorithm import RemoteAlgorithm
from esd_services_api_client.nexus.exceptions.startup_error import (
    FatalAlgorithmConfigurationError,
)
from esd_services_api_client.nexus.input.input_processor import (
    InputProcessor,
    resolve_processors,
)


class ForkedAlgorithm(NexusObject[TPayload, AlgorithmResult]):
    """
    Forked algorithm is an algorithm that returns a result (main scenario run) and then fires off one or more forked runs
    with different configurations as specified in fork class implementation.

    Forked algorithm only awaits scheduling of forked runs, but never their results.
    """

    def __init__(
        self,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        forks: list[RemoteAlgorithm],
        *input_processors: InputProcessor,
    ):
        super().__init__(metrics_provider, logger_factory)
        self._input_processors = input_processors
        if len(forks) > 0:
            raise FatalAlgorithmConfigurationError(
                message="Forked algorithm must define one or more forks",
                algorithm_class=self.__class__,
            )
        self._forks = forks

    @abstractmethod
    async def _run(self, **kwargs) -> AlgorithmResult:
        """
        Core logic for this algorithm. Implementing this method is mandatory.
        """

    @property
    def _metric_tags(self) -> dict[str, str]:
        return {"algorithm": self.__class__.alias()}

    async def run(self, **kwargs) -> AlgorithmResult:
        """
        Coroutine that executes the algorithm logic.
        """

        @run_time_metrics_async(
            metric_name="algorthm_run",
            on_finish_message_template="Finished running algorithm {algorithm} in {elapsed:.2f}s seconds",
            template_args={
                "algorithm": self.__class__.alias().upper(),
            },
        )
        async def _measured_run(**run_args) -> AlgorithmResult:
            return await self._run(**run_args)

        results = await resolve_processors(*self._input_processors, **kwargs)

        run_result = await partial(
            _measured_run,
            **reduce(lambda a, b: a | b, [result for _, result in results.items()]),
            metric_tags=self._metric_tags,
            metrics_provider=self._metrics_provider,
            logger=self._logger,
        )()

        # now await callback scheduling
        await asyncio.wait([fork.run(**kwargs) for fork in self._forks])

        return run_result
