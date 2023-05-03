"""
  Connector for Arcane Streaming API.
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
from http.client import HTTPException
from typing import Optional, List, Dict, Iterable

from adapta.utils import session_with_retries, doze
from requests import Session
from requests.auth import HTTPBasicAuth

from esd_services_api_client.arcane._api_versions import ApiVersion, rewrite_url
from esd_services_api_client.arcane._models import (
    StreamInfo,
    StreamState,
    StreamConfiguration,
)
from esd_services_api_client.boxer import BoxerTokenAuth


class ArcaneConnector:
    """
    Arcane Streaming API connector
    """

    def __init__(
        self,
        *,
        base_url,
        retry_attempts=10,
        auth: Optional[BoxerTokenAuth] = None,
        session: Optional[Session] = None,
        api_version: ApiVersion = ApiVersion.V1,
    ):
        """
          Creates Arcane Streaming connector, capable of managing Akka streams launched via Arcane.

        :param base_url: Base URL for Arcane Streaming endpoint.
        :param retry_attempts: Number of retries for Arcane-specific error messages.
        """
        self.base_url = rewrite_url(base_url, api_version)
        self.http = session or session_with_retries()
        if auth:
            self.http.hooks["response"].append(auth.get_refresh_hook(self.http))
            self.http.auth = auth
        else:
            self.http.auth = HTTPBasicAuth(
                os.environ.get("ARCANE_USER"), os.environ.get("ARCANE_PASSWORD")
            )
        self.retry_attempts = retry_attempts

    def start_stream(self, conf: StreamConfiguration) -> StreamInfo:
        """
         Starts a new stream again Sql Server table with change tracking enabled.

        :param conf: Stream configuration
        :return:
        """
        attempts = 0
        while attempts < self.retry_attempts:
            request_json = conf.to_dict()
            submission_result = self.http.post(
                f"{self.base_url}/stream/{conf.url_path}", json=request_json
            )
            submission_json = submission_result.json()

            if submission_result.status_code == 200 and submission_json:
                print(f"Stream activated: {submission_json['id']}")

                return StreamInfo.from_dict(submission_json)

            if submission_result.status_code == 503:
                attempts += 1
                retry_after_seconds = int(submission_result.headers.get("Retry-After"))

                print(f"Target instance full, will retry in {retry_after_seconds}")

                doze(retry_after_seconds)

                continue

            raise HTTPException(
                f"Error {submission_result.status_code} when submitting a request: {submission_result.text}"
            )

        raise TimeoutError(
            "Timed out waiting for Arcane to accept the stream start request"
        )

    def get_stream(self, source: str, stream_id: str) -> Optional[StreamInfo]:
        """
          Reads information about the specified stream and source.

        :param source: Stream source.
        :param stream_id: Stream identifier.
        :return:
        """
        info = self.http.get(f"{self.base_url}/stream/info/{source}/{stream_id}")
        info.raise_for_status()

        return StreamInfo.from_dict(info.json())

    def get_streams_by_tag(self, source: str, tag: str) -> List[StreamInfo]:
        """
         Reads streams matching the provided tag.

        :param source: Source for searched streams.
        :param tag: Tag assigned to streams.
        :return:
        """
        info = self.http.get(f"{self.base_url}/stream/info/{source}/tags/{tag}")
        info.raise_for_status()

        return [StreamInfo.from_dict(stream_info) for stream_info in info.json()]

    def restart_stream(
        self, conf: Dict, source: str, stream_id: str
    ) -> Optional[StreamInfo]:
        """
          Requests a stream restart with a new configuration.

        :param conf: Stream configuration to apply
        :param source: Source for this stream.
        :param stream_id: Stream identifier.
        :return:
        """
        info = self.http.post(
            f"{self.base_url}/stream/restart/{source}/{stream_id}", json=conf
        )
        info.raise_for_status()

        return StreamInfo.from_dict(info.json())

    def reload_stream(self, source: str, stream_id: str) -> Optional[StreamInfo]:
        """
          Requests a stream restart with a new configuration.

        :param source: Source for this stream.
        :param stream_id: Stream identifier.
        :return:
        """
        info = self.http.post(f"{self.base_url}/stream/reload/{source}/{stream_id}")
        info.raise_for_status()

        return StreamInfo.from_dict(info.json())

    def stop_stream(self, source: str, stream_id: str) -> Optional[StreamInfo]:
        """
          Requests a stream stop.

        :param source: Source for this stream.
        :param stream_id: Stream identifier.
        :return:
        """
        info = self.http.post(f"{self.base_url}/stream/stop/{source}/{stream_id}")
        info.raise_for_status()

        return StreamInfo.from_dict(info.json())

    def stop_streams_with_tag(self, source: str, tag: str) -> Iterable[StreamInfo]:
        """
          Stops streams with a matching client tag.

        :param source: Stream source.
        :param tag: Client tag to look for.
        :return: A list of stopped streams
        """

        active_streams = [
            stream
            for stream in self.get_streams_by_tag(source, tag)
            if stream.stream_state == StreamState.RUNNING.value
        ]

        for active_stream in active_streams:
            info = self.http.post(
                f"{self.base_url}/stream/stop/{source}/{active_stream.id}"
            )
            if info.status_code == 202:
                yield info.json()

    def update_stream(self, source: str, stream_id: str, request: StreamInfo):
        """
        Update stream metadata

        :param source:
        :param stream_id:
        :param request:
        :return:
        """
        response = self.http.patch(
            f"{self.base_url}/stream/metadata/{source}/{stream_id}",
            json=request.to_dict(),
        )
        response.raise_for_status()
