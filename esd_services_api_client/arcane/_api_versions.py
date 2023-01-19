"""
API versioning for arcane connector
"""
from enum import Enum


class ApiVersion(Enum):
    """
      API Versions
      V1 - Initial version
      V2 - Basic authentication replaced with Boxer token authentication
    """
    V1 = ""
    V2 = "v2"


def rewrite_url(base_url: str, version: ApiVersion) -> str:
    """
    Appends version segment to arcane URL
    :param base_url: base URL passed to connector
    :param version: API version number
    :return: Modified base URL
    """
    return "/".join([base_url.strip("/"), version.value]).removesuffix("/")
