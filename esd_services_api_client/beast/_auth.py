"""
 Beast Auth class
 Based on https://docs.python-requests.org/en/master/user/advanced/#custom-authentication
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

from datetime import datetime
from typing import Optional

from requests.auth import AuthBase

from azure.identity import DefaultAzureCredential


class BeastAuth(AuthBase):
    """Attaches HTTP Bearer Authentication to the given Request object sent to Beast"""

    def __init__(self, token_cache: Optional[list] = None, token_lifetime=3600):
        # setup any auth-related data here
        self.cache = token_cache or []
        self.token_lifetime = token_lifetime

    def _fetch_token(self) -> str:
        """
          Fetches a token from the cloud

        :return:
        """
        credential = DefaultAzureCredential(
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
            exclude_powershell_credential=True,
        )
        token: str = credential.get_token(
            "https://management.core.windows.net/.default"
        ).token
        self.cache.append((token, datetime.utcnow()))

        return token

    def _fetch_cached_token(self) -> Optional[str]:
        """
          Fetches a token from in-memory cache, if not expired

        :return:
        """
        if self.cache:
            valid_tokens = [
                (token, created_at)
                for token, created_at in self.cache
                if (datetime.utcnow() - created_at).seconds < self.token_lifetime
            ]
            if valid_tokens:
                return valid_tokens[0][0]

            self.cache.clear()
            return None

        return None

    def __call__(self, r):
        """
          Auth entrypoint

        :param r: Request to authorize
        :return: Request with Auth header set
        """
        cached_token = self._fetch_cached_token()
        if cached_token:
            r.headers["Authorization"] = f"Bearer {cached_token}"
        else:
            r.headers["Authorization"] = f"Bearer {self._fetch_token()}"

        return r
