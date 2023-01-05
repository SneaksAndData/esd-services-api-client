from enum import Enum

from requests.adapters import HTTPAdapter


class ApiVersion(Enum):
    """
      API Versions
      V1 - Initial version
      V2 - Basic authentication replaced with Boxer token authentication
    """
    V1 = ""
    V2 = "v2"


def rewrite_url(base_url: str, version: ApiVersion) -> str:
    return "/".join([base_url.strip("/"), version.value])
