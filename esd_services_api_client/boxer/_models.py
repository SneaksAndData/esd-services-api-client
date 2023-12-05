"""
 Models for Boxer
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

from dataclasses import dataclass
from typing import Dict


@dataclass
class Claim:
    """
    Boxer Claim
    """

    claim_name: str
    claim_value: str

    def to_dict(self) -> Dict:
        """Convert to Dictionary
        :return: Dictionary
        """
        return {self.claim_name: self.claim_value}

    @classmethod
    def from_dict(cls, json_data: Dict) -> "Claim":
        """Initialize from Dictionary
        :param json_data: Dictionary
        :return:
        """
        name = list(json_data.keys())[0]
        return Claim(
            claim_name=name,
            claim_value=json_data[f"{name}"],
        )


class BoxerToken:
    """
    Represents token created by BoxerConnector.get_token
    """

    def __init__(self, token: str):
        self._token = token

    def __str__(self):
        return self._token
