from abc import ABC, abstractmethod

from esd_services_api_client.boxer import BoxerToken


class BoxerTokenProvider(ABC):

    @abstractmethod
    def get_token(self) -> BoxerToken:
        pass
