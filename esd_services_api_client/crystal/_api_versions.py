"""
API versioning for arcane connector
"""
from enum import Enum


class ApiVersion(Enum):
    """
      API Versions
      V1_2 - Boxer token authentication and updated API for run submission and result read
    """
    V1_2 = "v1.2"
