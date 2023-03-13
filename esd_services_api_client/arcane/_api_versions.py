"""
API versioning for arcane connector
"""
#  Copyright (c) 2023. ECCO Sneaks & Data
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

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
