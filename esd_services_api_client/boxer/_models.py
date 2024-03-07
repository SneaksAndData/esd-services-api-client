"""
 Models for Boxer
"""
#  Copyright (c) 2023-2024. ECCO Sneaks & Data
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

from dataclasses_json import LetterCase, dataclass_json, DataClassJsonMixin


@dataclass_json
@dataclass
class Claim(DataClassJsonMixin):
    """
    Boxer Claim
    """

    claim_name: str
    claim_value: str


@dataclass_json
@dataclass
class ClaimPayload(DataClassJsonMixin):
    """
    Boxer Claim Payload for Deleting/Inserting claims
    """

    operation: str
    claims: dict

    def add_claim(self, claim: Claim) -> "ClaimPayload":
        """
        Add a claim to the ClaimPayload
        """
        self.claims |= {claim.claim_name: claim.claim_value}
        return self


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ClaimResponse(DataClassJsonMixin):
    """
    Boxer Claim request response
    """

    identity_provider: str
    user_id: str
    claims: list[dict]
    billing_id: str


class BoxerToken:
    """
    Represents token created by BoxerConnector.get_token
    """

    def __init__(self, token: str):
        self._token = token

    def __str__(self):
        return self._token
