"""
  Connector for Boxer Auth API.
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

import os
from functools import reduce
from typing import Optional, Iterator, final

from adapta.security.clients import AzureClient
from adapta.utils import session_with_retries
from requests import Session, Response

from esd_services_api_client.boxer._base import BoxerTokenProvider
from esd_services_api_client.boxer._auth import (
    BoxerAuth,
    ExternalTokenAuth,
    BoxerTokenAuth,
    ExternalAuthBase,
    RefreshableExternalTokenAuth,
)
from esd_services_api_client.boxer._models import (
    BoxerToken,
    Claim,
    ClaimPayload,
    ClaimResponse,
)


@final
class BoxerClaimConnector:
    """
    Boxer Claims API connector
    """

    def __init__(self, *, base_url: str, auth: Optional[BoxerTokenAuth] = None):
        """Creates Boxer Claims connector, capable of managing claims
        :param base_url: Base URL for Boxer Claims endpoint
        :param auth: Boxer-based authentication
        """
        self._base_url = base_url
        self._http = session_with_retries()
        if auth and isinstance(auth, BoxerTokenAuth):
            self._http.hooks["response"].append(auth.get_refresh_hook(self._http))
        self._http.auth = auth

    def get_claims(self, user_id: str, provider: str) -> Optional[Iterator[Claim]]:
        """
        Returns the claims assigned to the specified user_id and provider
        """
        response = self._http.get(f"{self._base_url}/claim/{provider}/{user_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return self._iterate_user_claims_response(response)

    def add_user(self, user_id: str, provider: str) -> ClaimResponse:
        """
        Adds a new user_id, provider pair
        """
        response = self._http.post(f"{self._base_url}/claim/{provider}/{user_id}")
        response.raise_for_status()
        return ClaimResponse.from_dict(response.json())

    def remove_user(self, user_id: str, provider: str) -> Response:
        """
        Removes the specified user_id, provider pair and assigned claims
        """
        response = self._http.delete(f"{self._base_url}/claim/{provider}/{user_id}")
        response.raise_for_status()
        return response

    def add_claim(
        self, user_id: str, provider: str, claims: list[Claim]
    ) -> Optional[ClaimResponse]:
        """
        Adds a new claim to an existing user_id, provider pair
        """
        payload_json = self._prepare_claim_payload(user_id, provider, claims, "Insert")
        response = self._http.patch(
            f"{self._base_url}/claim/{provider}/{user_id}",
            data=payload_json,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return ClaimResponse.from_dict(response.json())

    def remove_claim(
        self, user_id: str, provider: str, claims: list[Claim]
    ) -> Optional[ClaimResponse]:
        """
        Removes the specified claim
        """
        payload_json = self._prepare_claim_payload(user_id, provider, claims, "Delete")
        response = self._http.patch(
            f"{self._base_url}/claim/{provider}/{user_id}",
            data=payload_json,
            headers={"Content-Type": "application/json"},
        )
        return ClaimResponse.from_dict(response.json())

    def _prepare_claim_payload(
        self, user_id: str, provider: str, claims: list[Claim], operation: str
    ) -> Optional[str]:
        """
        Prepare payload for Inserting/Deleting claims
        """
        if self.get_claims(user_id, provider) is not None:
            payload = ClaimPayload(operation, {})
            claim_payload = reduce(
                lambda cp, claim: cp.add_claim(claim), claims, payload
            )

            return claim_payload.to_json()
        return None

    def _iterate_user_claims_response(
        self, user_claim_response: Response
    ) -> Optional[Iterator[Claim]]:
        """Creates an iterator to iterate user claims from Json Response
        :param user_claim_response: HTTP Response
        """
        response_json = user_claim_response.json()
        if response_json and "claims" in response_json:
            for claim in response_json["claims"]:
                if isinstance(claim, dict) and len(claim) == 1:
                    for key, value in claim.items():
                        yield Claim.from_dict({"claim_name": key, "claim_value": value})
                        break
        else:
            raise ValueError("Expected response body of type application/json")


class BoxerConnector(BoxerTokenProvider):
    """
    Boxer Auth API connector
    """

    def __init__(
        self,
        *,
        base_url,
        auth: ExternalAuthBase,
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
        if isinstance(auth, RefreshableExternalTokenAuth):
            self.http.hooks["response"].append(auth.get_refresh_hook(self.http))
        self.retry_attempts = retry_attempts

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
        external_auth = RefreshableExternalTokenAuth(
            proteus_client.get_access_token, auth_provider
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
