"""
Interfaces for boxer API
"""
from abc import ABC, abstractmethod

from esd_services_api_client.boxer import BoxerToken


class BoxerTokenProvider(ABC):
    """Token provider interface"""

    @abstractmethod
    def get_token(self) -> BoxerToken:
        pass
