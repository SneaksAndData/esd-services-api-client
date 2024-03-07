"""
 Boxer Auth classes
 Based on https://docs.python-requests.org/en/master/user/advanced/#custom-authentication
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

import base64
from abc import abstractmethod
from functools import partial
from typing import Callable, Any

import requests
from Crypto.Hash.SHA256 import new as sha256_get_instance
from Crypto.PublicKey import RSA
from Crypto.Signature.PKCS1_v1_5 import new as signature_factory
from requests import Session, Response, PreparedRequest
from requests.auth import AuthBase
from typing_extensions import Unpack

from esd_services_api_client.boxer._base import BoxerTokenProvider
from esd_services_api_client.boxer._models import BoxerToken


class BoxerAuth(AuthBase):
    """Attaches HTTP Bearer Authentication to the given Request object sent to Boxer"""

    def __init__(self, *, private_key_base64: str, consumer_id: str):
        # setup any auth-related data here
        self._sign_key = private_key_base64
        self._consumer_id = consumer_id

    def _sign_string(self, input_string: str) -> str:
        """
          Signs input for Boxer

        :param input_string: input to generate signature for
        :return:
        """
        msg_bytes = input_string.encode("utf-8")
        digest = sha256_get_instance()

        private_key_bytes = base64.b64decode(self._sign_key)
        rsa_key = RSA.importKey(private_key_bytes, "")
        signer = signature_factory(rsa_key)

        digest.update(msg_bytes)
        signed = signer.sign(digest)
        return base64.b64encode(signed).decode("utf-8")

    def __call__(self, request: PreparedRequest):
        """
          Auth entrypoint

        :param request: Request to authorize
        :return: Request with Auth header set
        """
        payload = request.url.replace("https://", "").split("?")[0]
        signature_base64 = self._sign_string(payload)
        request.headers["Authorization"] = f"Signature {signature_base64}"
        request.headers["X-Boxer-ConsumerId"] = self._consumer_id
        request.headers["X-Boxer-Payload"] = payload

        return request


class ExternalAuthBase(AuthBase):
    """Base class for external authentication methods"""

    def __init__(self, authentication_provider):
        self._authentication_provider = authentication_provider

    @abstractmethod
    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        pass

    @property
    def authentication_provider(self) -> str:
        """
        :return authentication provider name
        """
        return self._authentication_provider


class ExternalTokenAuth(ExternalAuthBase):
    """
    Create authentication for external token e.g. for azuread or kubernetes auth policies
    NOTE: this class is deprecated, use RefreshableExternalTokenAuth instead
    """

    def __init__(self, token: str, authentication_provider: str):
        super().__init__(authentication_provider)
        self._token = token

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        """
          Auth entrypoint

        :param r: Request to authorize
        :return: Request with Auth header set
        """
        r.headers["Authorization"] = f"Bearer {self._token}"
        return r


class RefreshableExternalTokenAuth(ExternalAuthBase):
    """
    Create authentication for external token e.g. for azuread or kubernetes auth policies
    If the external token is expired, this auth method will try to get new external token and retry the request once
    """

    def __init__(self, get_token: Callable[[], str], authentication_provider: str):
        super().__init__(authentication_provider)
        self._get_token = get_token
        self._retrying = False

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        """
          Auth entrypoint

        :param r: Request to authorize
        :return: Request with Auth header set
        """
        r.headers["Authorization"] = f"Bearer {self._get_token()}"
        return r

    def refresh_token(self, response: Response, session: Session, *_, **__):
        """
        Refresh token hook if request fails with unauthorized or forbidden status code and retries the request.
        :param response:  Response received from API server
        :param session: Session used for original API interaction
        :param _: Positional arguments
        :param __: Keyword arguments
        :return:
        """
        if self._retrying:
            return response
        if response.status_code == requests.codes["unauthorized"]:
            self._retrying = True
            response = session.send(self(response.request))
            self._retrying = False
            return response
        return response

    def get_refresh_hook(
        self, session: Session
    ) -> Callable[[Response, Unpack[Any]], Response]:
        """
        Generate request hook
        :param session: Session used for original API interaction
        :returns
        """
        return partial(self.refresh_token, session=session)


class BoxerTokenAuth(AuthBase):
    """
    Implements Boxer auth token retrieving and renewing
    """

    def __init__(self, token_provider: BoxerTokenProvider):
        self._token_provider = token_provider
        self._token = None

    def __call__(self, request: PreparedRequest) -> PreparedRequest:
        """
          Auth entrypoint

        :param request: Request to authorize
        :return: Request with Auth header set
        """
        request.headers["Authorization"] = f"Bearer {self._get_token()}"
        return request

    def refresh_token(self, response: Response, session: Session, *_, **__):
        """
        Refresh token hook if request fails with unauthorized or forbidden status code and retries the request.
        :param response:  Response received from API server
        :param session: Session used for original API interaction
        :param _: Positional arguments
        :param __: Keyword arguments
        :return:
        """
        if response.status_code == requests.codes["unauthorized"]:
            self._get_token(refresh=True)
            return session.send(self(response.request))
        return response

    def get_refresh_hook(
        self, session: Session
    ) -> Callable[[Response, Unpack[Any]], Response]:
        """
        Generate request hook
        :param session: Session used for original API interaction
        :returns
        """
        return partial(self.refresh_token, session=session)

    def _get_token(self, refresh=False) -> BoxerToken:
        """
        Retrieves token and stores it for future use
        :param refresh: True if we need to refresh token
        :return: token for Boxer API
        """
        if not self._token or refresh:
            self._token = self._token_provider.get_token()
        return self._token
