"""
 Base algorithm
"""

#  Copyright (c) 2023. ECCO Sneaks & Data
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

from adapta.metrics import MetricsProvider
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.abstractions.nexus_object import NexusObject
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.input.input_processor import InputProcessor


class BaselineAlgorithm(NexusObject):
    """
    Base class for all algorithm implementations.
    """

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
        async with self._input_processor as input_processor:
            return await self._run(**(await input_processor.process_input(**kwargs)))
