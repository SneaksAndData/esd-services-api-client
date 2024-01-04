from abc import abstractmethod

from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.algorithms._baseline_algorithm import (
    BaselineAlgorithm,
)


class RecursiveAlgorithm(BaselineAlgorithm):
    async def _run(self, **kwargs) -> PandasDataFrame:
        pass

    @abstractmethod
    async def _is_finished(self, **kwargs) -> bool:
        """

        """
    async def run(self, **kwargs) -> PandasDataFrame:
        result = await self._run(**self._input_processor.process_input(**kwargs))
        if self._is_finished(**result):
            return result
        return await self.run(**result)
