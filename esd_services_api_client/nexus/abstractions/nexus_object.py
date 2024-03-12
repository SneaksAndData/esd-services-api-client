"""
 Base classes for all objects used by Nexus.
"""
import re

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


from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Union, Any

import pandas
import polars
from adapta.metrics import MetricsProvider

from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory


class AlgorithmResult(ABC):
    """
    Interface for algorithm run result. You can store arbitrary data here, but `dataframe` method must be implemented.
    """

    @abstractmethod
    def dataframe(self) -> Union[pandas.DataFrame, polars.DataFrame]:
        """
        Returns the main result dataframe. This will be written to the linked output storage.
        """

    @abstractmethod
    def to_kwargs(self) -> dict[str, Any]:
        """
        Convert result to kwargs for the next iteration (for recursive algorithms)
        """


TPayload = TypeVar("TPayload")  # pylint: disable=C0103
TResult = TypeVar(  # pylint: disable=C0103
    "TResult", pandas.DataFrame, polars.DataFrame
)


class NexusObject(Generic[TPayload, TResult], ABC):
    """
    Base class for all Nexus objects.
    """

    def __init__(
        self,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
    ):
        self._metrics_provider = metrics_provider
        self._logger = logger_factory.create_logger(logger_type=self.__class__)

    async def __aenter__(self):
        self._logger.start()
        await self._context_open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._logger.stop()
        await self._context_close()

    @abstractmethod
    async def _context_open(self):
        """
        Optional actions to perform on context activation.
        """

    @abstractmethod
    async def _context_close(self):
        """
        Optional actions to perform on context closure.
        """

    @classmethod
    def alias(cls) -> str:
        """
        Alias to identify this reader's output
        """
        return re.sub(
            r"(?<!^)(?=[A-Z])",
            "_",
            cls.__name__.lower()
            .replace("reader", "")
            .replace("processor", "")
            .replace("algorithm", ""),
        )
