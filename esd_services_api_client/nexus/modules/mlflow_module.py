import os

from injector import Module, singleton, provider
from typing import final
from adapta.ml.mlflow import MlflowBasicClient
from esd_services_api_client.nexus.exceptions.startup_error import FatalStartupConfigurationError


@final
class MlflowModule(Module):
    """
    MLFlow module.
    """

    @singleton
    @provider
    def provide(self) -> MlflowBasicClient:
        """
        DI factory method.
        """
        if "NEXUS__MLFLOW_TRACKING_URI" not in os.environ:
            raise FatalStartupConfigurationError(
                "NEXUS__MLFLOW_TRACKING_URI"
            )
        return MlflowBasicClient(os.environ["NEXUS__MLFLOW_TRACKING_URI"])
