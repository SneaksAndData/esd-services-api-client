"""
 Utility functions to handle input processing.
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
from typing import Union, Type
import azure.core.exceptions
import deltalake

from esd_services_api_client.nexus.abstractions.nexus_object import TResult, TPayload
from esd_services_api_client.nexus.exceptions.input_reader_error import (
    FatalInputReaderError,
    TransientInputReaderError,
)
from esd_services_api_client.nexus.input.input_reader import InputReader


_reader_cache = {}


def resolve_reader_exc_type(
    ex: BaseException,
) -> Union[Type[FatalInputReaderError], Type[TransientInputReaderError]]:
    """
    Resolve base exception into a specific Nexus exception.
    """
    match type(ex):
        case azure.core.exceptions.HttpResponseError, deltalake.PyDeltaTableError:
            return TransientInputReaderError
        case azure.core.exceptions.AzureError, azure.core.exceptions.ClientAuthenticationError:
            return FatalInputReaderError
        case _:
            return FatalInputReaderError


async def resolve_readers(
    *readers: InputReader[TPayload, TResult]
) -> dict[str, TResult]:
    """
    Concurrently resolve `data` property of all readers by invoking their `read` method.
    """

    def get_result(alias: str, completed_task: asyncio.Task) -> TResult:
        reader_exc = completed_task.exception()
        if reader_exc:
            raise resolve_reader_exc_type(reader_exc)(alias, reader_exc) from reader_exc

        return completed_task.result()

    async def _read(input_reader: InputReader):
        async with input_reader as instance:
            result = await instance.read()
            _reader_cache[input_reader.__class__.alias()] = result
        return result

    cached = {
        reader.__class__.alias(): reader.data
        for reader in readers
        if reader.__class__.alias() in _reader_cache
    }
    if len(cached) == len(readers):
        return cached

    read_tasks: dict[str, asyncio.Task] = {
        reader.__class__.alias(): asyncio.create_task(_read(reader))
        for reader in readers
        if reader.__class__.alias() not in _reader_cache
    }
    if len(read_tasks) > 0:
        await asyncio.wait(fs=read_tasks.values())

    return {
        alias: get_result(alias, task) for alias, task in read_tasks.items()
    } | cached
