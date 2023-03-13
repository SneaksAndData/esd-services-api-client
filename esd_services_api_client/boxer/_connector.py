"""
  Connector for Boxer Auth API.
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

import os
from typing import Iterator, Optional

import jwt
from adapta.security.clients import AzureClient
from adapta.utils import session_with_retries
from requests import Session

from esd_services_api_client.boxer._base import BoxerTokenProvider
from esd_services_api_client.boxer._auth import (
    BoxerAuth,
    ExternalTokenAuth,
    BoxerTokenAuth,
)
from esd_services_api_client.boxer._helpers import (
    _iterate_user_claims_response,
    _iterate_boxer_claims_response,
)
from esd_services_api_client.boxer._models import BoxerClaim, UserClaim, BoxerToken


class BoxerConnector(BoxerTokenProvider):
    """
    Boxer Auth API connector
    """

    def __init__(
        self,
        *,
        base_url,
        auth: ExternalTokenAuth,
        retry_attempts=10,
        session: Optional[Session] = None,
    ):
        """Creates Boxer Auth connector, capable of managing claims/consumers
        :param base_url: Base URL for Boxer Auth endpoint
        :param retry_attempts: Number of retries for Boxer-specific error messages
        """
        self.base_url = base_url
        self.http = session or session_with_retries()
        self.http.auth = auth or self._create_boxer_auth()
        if auth:
            self.authentication_provider = auth.authentication_provider
        self.retry_attempts = retry_attempts

    def push_user_claim(self, claim: BoxerClaim, user_id: str):
        """Adds/Overwrites a new Boxer Claim to a user
        :param claim: Boxer Claim
        :param user_id: User's UPN
        :return:
        """
        target_url = f"{self.base_url}/claims/user/{user_id}"
        claim_json = claim.to_dict()
        response = self.http.post(target_url, json=claim_json)
        response.raise_for_status()
        print(f"Successfully pushed user claim for user {user_id}")

    def push_group_claim(self, claim: BoxerClaim, group_name: str):
        """Adds/Overwrites a new Boxer Claim to a user
        :param claim: Boxer Claim
        :param group_name: Group Name
        :return:
        """
        target_url = f"{self.base_url}/claims/group/{group_name}"
        claim_json = claim.to_dict()
        response = self.http.post(target_url, json=claim_json)
        response.raise_for_status()
        print(f"Successfully pushed user claim for group {group_name}")

    def get_claims_by_type(self, claims_type: str) -> Iterator[UserClaim]:
        """Reads claims of specified type from Boxer.
        :param claims_type: claim type to filter claims by.
        :return: Iterator[UserClaim]
        """
        target_url = f"{self.base_url}/claims/type/{claims_type}"
        response = self.http.get(target_url)
        response.raise_for_status()
        return _iterate_user_claims_response(response)

    def get_claims_by_user(self, user_id: str) -> Iterator[BoxerClaim]:
        """Reads user claims from Boxer
        :param user_id: user upn to load claims for
        :return: Iterator[UserClaim]
        """
        empty_user_token = jwt.encode({"upn": user_id}, "_", algorithm="HS256")
        target_url = f"{self.base_url}/claims/user/{empty_user_token}"
        response = self.http.get(target_url)
        response.raise_for_status()
        return _iterate_boxer_claims_response(response)

    def get_claims_by_group(self, group_name: str) -> Iterator[BoxerClaim]:
        """Reads group claims from Boxer
        :param group_name: group name to load claims for
        :return: Iterator[UserClaim]
        """
        target_url = f"{self.base_url}/claims/group/{group_name}"
        response = self.http.get(target_url)
        response.raise_for_status()
        return _iterate_boxer_claims_response(response)

    def get_claims_for_token(self, jwt_token: str) -> Iterator[BoxerClaim]:
        """Reads user claims from Boxer based on jwt token
        :param jwt_token: jwt token with UPN set
        :return: Iterator[UserClaim]
        """
        target_url = f"{self.base_url}/claims/user/{jwt_token}"
        response = self.http.get(target_url)
        response.raise_for_status()
        return _iterate_boxer_claims_response(response)

    def create_consumer(self, consumer_id: str, overwrite: bool = False) -> str:
        """Adds/Overwrites a new Boxer Claim to a user
        :param consumer_id: Consumer ID of new consumer
        :param overwrite: Flag to overwrite if consumer with given consumer_id already exists
        :return: New consumer's private key (Base64 Encoded)
        """
        target_url = f"{self.base_url}/consumer/{consumer_id}?overwrite={overwrite}"
        response = self.http.post(target_url, json={})
        response.raise_for_status()
        return response.text

    def get_consumer_public_key(self, consumer_id: str) -> str:
        """Reads Consumer's public key
        :param consumer_id: Boxer Claim
        :return: public key (Base64 Encoded)
        """
        target_url = f"{self.base_url}/consumer/publicKey/{consumer_id}"
        response = self.http.get(target_url, json={})
        response.raise_for_status()
        return response.text

    def get_token(self) -> BoxerToken:
        """
        Authorize with external token and return BoxerToken
        :return: BoxerToken
        """
        if not self.authentication_provider:
            raise ValueError(
                "If boxer token is used, ExternalTokenAuth should be provided"
            )
        target_url = f"{self.base_url}/token/{self.authentication_provider}"
        response = self.http.get(target_url)
        response.raise_for_status()
        return BoxerToken(response.text)

    @staticmethod
    def _create_boxer_auth():
        assert os.environ.get(
            "BOXER_CONSUMER_ID"
        ), "Environment BOXER_CONSUMER_ID not set"
        assert os.environ.get(
            "BOXER_PRIVATE_KEY"
        ), "Environment BOXER_PRIVATE_KEY not set"
        return BoxerAuth(
            private_key_base64=os.environ.get("BOXER_PRIVATE_KEY"),
            consumer_id=os.environ.get("BOXER_CONSUMER_ID"),
        )


def select_authentication(auth_provider: str, env: str) -> Optional[BoxerTokenAuth]:
    """
    Select authentication provider for console clients in backward-compatible way
    This method will be removed after migration of console clients to boxer authentication
    :param auth_provider: Name of authorization provider
    :param env: Name of deploy environment
    :return: BoxerAuthentication or None
    """
    if auth_provider == "azuread":
        proteus_client = AzureClient(subscription_id="")
        external_auth = ExternalTokenAuth(
            proteus_client.get_access_token(), auth_provider
        )
        boxer_connector = BoxerConnector(
            base_url=f"https://boxer.{env}.sneaksanddata.com", auth=external_auth
        )
        return BoxerTokenAuth(boxer_connector)
    return None


def get_kubernetes_token(cluster_name: str, boxer_base_url: str) -> BoxerTokenAuth:
    """
    Create Boxer auth based on kubernetes cluster token for ExternalTokenAuth.
    :param cluster_name: Name of the cluster (should match name of Identity provider in boxer configuration)
    :param boxer_base_url: Boxer base url
    :return: BoxerTokenAuth configured fot particular identity provider and kubernetes auth token
    """
    with open(
        "/var/run/secrets/kubernetes.io/serviceaccount/token", "r", encoding="utf-8"
    ) as token_file:
        external_auth = ExternalTokenAuth(token_file.readline(), cluster_name)
        boxer_connector = BoxerConnector(base_url=boxer_base_url, auth=external_auth)
        return BoxerTokenAuth(boxer_connector)
