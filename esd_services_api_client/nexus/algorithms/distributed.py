import asyncio
from abc import ABC, abstractmethod

from esd_services_api_client.nexus.algorithms import BaselineAlgorithm
from pandas import DataFrame as PandasDataFrame


class DistributedAlgorithm(BaselineAlgorithm, ABC):
    @abstractmethod
    async def _split(self, **_) -> list[BaselineAlgorithm]:
        """ """

    @abstractmethod
    async def _fold(self, *split_tasks: asyncio.Task) -> PandasDataFrame:
        """ """

    async def _run(self, **kwargs) -> PandasDataFrame:
        splits = await self._split(**kwargs)
        tasks = [asyncio.create_task(split.run(**kwargs)) for split in splits]

        await asyncio.wait(*tasks)

        return await self._fold(*tasks)
