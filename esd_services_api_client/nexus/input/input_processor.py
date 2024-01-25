"""
 Input processing.
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
from typing import Dict

from adapta.metrics import MetricsProvider

from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.abstractions.nexus_object import (
    NexusObject,
    TPayload,
)
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.input._functions import resolve_readers
from esd_services_api_client.nexus.input.input_reader import InputReader


class InputProcessor(NexusObject[TPayload]):
    """
    Base class for raw data processing into algorithm input.
    """

    def __init__(
        self,
        *readers: InputReader,
        payload: TPayload,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        super().__init__(metrics_provider, logger_factory)
        self._readers = readers
        self._payload = payload

    async def _read_input(self) -> Dict[str, PandasDataFrame]:
        return await resolve_readers(*self._readers)

    @abstractmethod
    async def process_input(self, **kwargs) -> Dict[str, PandasDataFrame]:
        """
        Input processing logic. Implement this method to prepare data for your algorithm code.
        """
