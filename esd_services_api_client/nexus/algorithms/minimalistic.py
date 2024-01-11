from abc import ABC

from esd_services_api_client.nexus.algorithms._baseline_algorithm import (
    BaselineAlgorithm,
)


class MinimalisticAlgorithm(BaselineAlgorithm, ABC):
    """
    Simple algorithm with a single method to train/solve/predict.
    """
