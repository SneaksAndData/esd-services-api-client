"""
 Input reader.
"""
import functools

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

import re
from abc import abstractmethod
from functools import partial
from typing import Optional

from adapta.metrics import MetricsProvider
from adapta.process_communication import DataSocket
from adapta.storage.query_enabled_store import QueryEnabledStore
from adapta.utils.decorators._logging import run_time_metrics_async

from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.abstractions.nexus_object import (
    NexusObject,
    TPayload,
)
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory


class InputReader(NexusObject[TPayload]):
    """
    Base class for a raw data reader.
    """

    def __init__(
        self,
        store: QueryEnabledStore,
        metrics_provider: MetricsProvider,
        logger_factory: LoggerFactory,
        payload: TPayload,
        *readers: "InputReader",
        socket: Optional[DataSocket] = None,
    ):
        super().__init__(metrics_provider, logger_factory)
        self.socket = socket
        self._store = store
        self._data: Optional[PandasDataFrame] = None
        self._readers = readers
        self._payload = payload

    @property
    def alias(self) -> str:
        """
        Alias to identify this reader's output
        """
        if self.socket:
            return self.socket.alias

        return self._metric_name

    @functools.cached_property
    def data(self) -> Optional[PandasDataFrame]:
        """
        Data read by this reader.
        """
        return self._data

    @abstractmethod
    async def _read_input(self) -> PandasDataFrame:
        """
        Actual data reader logic. Implementing this method is mandatory for the reader to work
        """

    @property
    def _metric_name(self) -> str:
        return re.sub(
            r"(?<!^)(?=[A-Z])",
            "_",
            self.__class__.__name__.lower().replace("reader", ""),
        )

    @property
    def _metric_tags(self) -> dict[str, str]:
        return {"entity": self._metric_name}

    async def read(self) -> PandasDataFrame:
        """
        Coroutine that reads the data from external store and converts it to a dataframe.
        """

        @run_time_metrics_async(
            metric_name="read_input",
            on_finish_message_template="Finished reading {entity} from path {data_path} in {elapsed:.2f}s seconds",
            template_args={
                "entity": self._metric_name.upper(),
            }
            | {"data_path": self.socket.data_path}
            if self.socket
            else {},
        )
        async def _read(**_) -> PandasDataFrame:
            if not self._data:
                self._data = await self._read_input()

            return self._data

        return await partial(
            _read,
            metric_tags=self._metric_tags,
            metrics_provider=self._metrics_provider,
            logger=self._logger,
        )()
