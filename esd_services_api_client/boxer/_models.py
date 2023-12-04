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
    claim_name: str
    claim_value: str

    def to_dict(self) -> Dict:
        """Convert to Dictionary
        :return: Dictionary
        """
        return {
            self.claim_name: self.claim_value
        }

    @classmethod
    def from_dict(cls, json_data: Dict) -> "Claim":
        """Initialize from Dictionary
        :param json_data: Dictionary
        :return:
        """
        name = json_data.keys()[0]
        return Claim(
            claim_name=name,
            claim_value=json_data[f"{name}"],
        )


@dataclass
class BoxerClaim:
    """
    Boxer Claim
    """

    claim_type: str
    claim_value: str
    issuer: str

    def to_dict(self) -> Dict:
        """Convert to Dictionary
        :return: Dictionary
        """
        return {
            "claimType": self.claim_type,
            "claimValue": self.claim_value,
            "issuer": self.issuer,
        }

    @classmethod
    def from_dict(cls, json_data: Dict):
        """Initialize from Dictionary
        :param json_data: Dictionary
        :return:
        """
        return BoxerClaim(
            claim_type=json_data["claimType"],
            claim_value=json_data["claimValue"],
            issuer=json_data["issuer"],
        )


@dataclass
class UserClaim:
    """
    Boxer User Claim
    """

    user_id: str
    user_claim_id: str
    claim: BoxerClaim

    def to_dict(self) -> Dict:
        """Convert to Dictionary
        :return: Dictionary
        """
        return {
            "userId": self.user_id,
            "userClaimId": self.user_claim_id,
            "claim": self.claim.to_dict(),
        }

    @classmethod
    def from_dict(cls, json_data: Dict):
        """Initialize from Dictionary
        :param json_data: Dictionary
        :return:
        """
        return UserClaim(
            user_id=json_data["userId"],
            user_claim_id=json_data["userClaimId"],
            claim=BoxerClaim.from_dict(json_data["claim"]),
        )


@dataclass
class GroupClaim:
    """
    Boxer Group Claim
    """

    group_name: str
    group_claim_id: str
    claim: BoxerClaim

    def to_dict(self) -> Dict:
        """Convert to Dictionary
        :return: Dictionary
        """
        return {
            "groupName": self.group_name,
            "groupClaimId": self.group_claim_id,
            "claim": self.claim.to_dict(),
        }

    @classmethod
    def from_dict(cls, json_data: Dict):
        """Initialize from Dictionary
        :param json_data: Dictionary
        :return:
        """
        return GroupClaim(
            group_name=json_data["groupName"],
            group_claim_id=json_data["groupClaimId"],
            claim=BoxerClaim.from_dict(json_data["claim"]),
        )


class BoxerToken:
    """
    Represents token created by BoxerConnector.get_token
    """

    def __init__(self, token: str):
        self._token = token

    def __str__(self):
        return self._token
