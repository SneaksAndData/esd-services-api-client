from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.algorithms._baseline_algorithm import BaselineAlgorithm


class MinimalisticAlgorithm(BaselineAlgorithm):
    async def _run(self, **kwargs) -> PandasDataFrame:
        pass
