"""
API versioning for arcane connector
"""
from enum import Enum


class ApiVersion(Enum):
    """
      API Versions
      V1_1 - Initial version
      V1_2 - Basic authentication replaced with Boxer token authentication
    """
    V1_1 = "v1.1"
    V1_2 = "v1.2"
