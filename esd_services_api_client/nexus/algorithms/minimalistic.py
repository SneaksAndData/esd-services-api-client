from abc import ABC

from pandas import DataFrame as PandasDataFrame

from esd_services_api_client.nexus.algorithms._baseline_algorithm import (
    BaselineAlgorithm,
)


class MinimalisticAlgorithm(BaselineAlgorithm, ABC):
    """
    Simple algorithm with a single method to train/solve/predict.
    """
