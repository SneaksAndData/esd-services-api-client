"""
 Algorithm that uses its output to alter the input for the next iteration, until a certain condition is met.
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
from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.algorithms._baseline_algorithm import (
    BaselineAlgorithm,
)
from esd_services_api_client.nexus.input import InputProcessor


class RecursiveAlgorithm(BaselineAlgorithm):
    """
    Recursive algorithm base class.
    """

    @inject
    def __init__(
        self,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        *input_processors: InputProcessor,
    ):
        super().__init__(metrics_provider, logger_factory, *input_processors)

    @abstractmethod
    async def _is_finished(self, **kwargs) -> bool:
        """ """

    async def run(self, **kwargs) -> PandasDataFrame:
        result = await self._run(**kwargs)
        if self._is_finished(**result):
            return result
        return await self.run(**result)
