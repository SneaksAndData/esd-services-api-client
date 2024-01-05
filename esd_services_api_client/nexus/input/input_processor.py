import asyncio
from abc import abstractmethod, ABC
from typing import Dict

from injector import inject
from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.input.input_reader import InputReader


class InputProcessor(ABC):
    @inject
    def __init__(self, *readers: InputReader):
        self._readers = readers

    async def read_input(self) -> Dict[str, PandasDataFrame]:
        read_tasks: dict[str, asyncio.Task] = {
            reader.socket.alias: asyncio.create_task(reader.read())
            for reader in self._readers
        }
        await asyncio.wait(*read_tasks.values())
        # TODO: exception handling
        return {alias: task.result() for alias, task in read_tasks.items()}

    @abstractmethod
    def process_input(self, **kwargs) -> Dict[str, PandasDataFrame]:
        """ """
