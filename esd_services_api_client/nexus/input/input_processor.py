"""
 Input processing.
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
from functools import partial
from typing import Optional

from adapta.metrics import MetricsProvider
from adapta.utils.decorators import run_time_metrics_async

from esd_services_api_client.nexus.abstractions.nexus_object import (
    NexusObject,
    TPayload,
    TResult,
)
from esd_services_api_client.nexus.abstractions.logger_factory import LoggerFactory
from esd_services_api_client.nexus.input._functions import (
    resolve_readers,
    resolve_reader_exc_type,
)
from esd_services_api_client.nexus.input.input_reader import InputReader

_processor_cache = {}


class InputProcessor(NexusObject[TPayload, TResult]):
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
        self._result: Optional[TResult] = None

    async def _read_input(self) -> dict[str, TResult]:
        return await resolve_readers(*self._readers)

    @property
    def result(self) -> dict[str, TResult]:
        """
        Data returned by this processor
        """
        return self._result

    @abstractmethod
    async def _process_input(self, **kwargs) -> dict[str, TResult]:
        """
        Input processing logic. Implement this method to prepare data for your algorithm code.
        """

    @property
    def _metric_tags(self) -> dict[str, str]:
        return {"processor": self.__class__.alias()}

    async def process_input(self, **kwargs) -> dict[str, TResult]:
        """
        Input processing coroutine. Do not override this method.
        """

        @run_time_metrics_async(
            metric_name="input_process",
            on_finish_message_template="Finished processing {processor} in {elapsed:.2f}s seconds",
            template_args={
                "processor": self.__class__.alias().upper(),
            },
        )
        async def _process(**_) -> dict[str, TResult]:
            return await self._process_input(**kwargs)

        if self._result is None:
            self._result = await partial(
                _process,
                metric_tags=self._metric_tags,
                metrics_provider=self._metrics_provider,
                logger=self._logger,
            )()

        return self._result


async def resolve_processors(
    *processors: InputProcessor[TPayload, TResult], **kwargs
) -> dict[str, dict[str, TResult]]:
    """
    Concurrently resolve `result` property of all processors by invoking their `process_input` method.
    """

    def get_result(alias: str, completed_task: asyncio.Task) -> dict[str, TResult]:
        reader_exc = completed_task.exception()
        if reader_exc:
            raise resolve_reader_exc_type(reader_exc)(alias, reader_exc) from reader_exc

        return completed_task.result()

    async def _process(input_processor: InputProcessor):
        async with input_processor as instance:
            result = await instance.process_input(**kwargs)
            _processor_cache[input_processor.__class__.alias()] = result
        return result

    cached = {
        processor.__class__.alias(): processor.result
        for processor in processors
        if processor.__class__.alias() in _processor_cache
    }
    if len(cached) == len(processors):
        return cached

    process_tasks: dict[str, asyncio.Task] = {
        processor.__class__.alias(): asyncio.create_task(_process(processor))
        for processor in processors
        if processor.__class__.alias() not in _processor_cache
    }
    if len(process_tasks) > 0:
        await asyncio.wait(fs=process_tasks.values())

    return {
        alias: get_result(alias, task) for alias, task in process_tasks.items()
    } | cached
