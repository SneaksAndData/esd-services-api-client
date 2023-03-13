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

from unittest.mock import Mock, MagicMock

import pytest
import requests

from esd_services_api_client.arcane import (
    ArcaneConnector,
    StreamInfo,
    StreamError,
    ApiVersion,
)
from esd_services_api_client.boxer import (
    BoxerConnector,
    BoxerTokenAuth,
    ExternalTokenAuth,
)
import requests_mock


def test_retries():
    external_token_auth = ExternalTokenAuth(
        token="token", authentication_provider="test"
    )
    boxer_adapter, boxer_session = generate_boxer_mock_session(external_token_auth)

    boxer_connector = BoxerConnector(
        base_url="https://boxer.example.com",
        auth=external_token_auth,
        session=boxer_session,
    )
    boxer_auth = BoxerTokenAuth(boxer_connector)

    arcane_connector = ArcaneConnector(
        base_url="https://arcane.example.com",
        auth=boxer_auth,
        session=generate_arcane_mock_session(),
        api_version=ApiVersion.V2,
    )
    streams = []
    for _ in range(0, 5):
        streams.append(arcane_connector.get_stream("STREAM_SOURCE", "streamId"))

    assert len(streams) == 5
    assert len(boxer_adapter.request_history) == 3


@pytest.mark.parametrize(
    "api_version, expected_url",
    [
        (
            ApiVersion.V1,
            "https://arcane.example.com/stream/info/STREAM_SOURCE/stream_id",
        ),
        (
            ApiVersion.V2,
            "https://arcane.example.com/v2/stream/info/STREAM_SOURCE/stream_id",
        ),
    ],
)
def test_http_adapter(api_version, expected_url):
    mock_stream = StreamInfo(
        "id",
        "STREAM_SOURCE",
        "",
        "test",
        "test",
        "{}",
        "",
        "RUNNING",
        StreamError("", "", ""),
    ).to_dict()
    arcane_adapter = requests_mock.Adapter()
    arcane_adapter.register_uri(
        requests_mock.ANY,
        requests_mock.ANY,
        response_list=[
            {"json": mock_stream, "status_code": 200},
        ],
    )
    arcane_session = requests.Session()
    arcane_session.mount("https://", arcane_adapter)
    arcane_connector = ArcaneConnector(
        base_url="https://arcane.example.com",
        api_version=api_version,
        session=arcane_session,
    )
    arcane_connector.get_stream("STREAM_SOURCE", "stream_id")
    assert arcane_adapter.request_history[0].url == expected_url


def generate_boxer_mock_session(external_token_auth):
    boxer_adapter = requests_mock.Adapter()
    boxer_adapter.register_uri(
        requests_mock.ANY, "https://boxer.example.com/token/test", json={}
    )
    boxer_session = requests.Session()
    boxer_session.mount("https://", boxer_adapter)
    return boxer_adapter, boxer_session


def generate_arcane_mock_session():
    mock_stream = StreamInfo(
        "id",
        "STREAM_SOURCE",
        "",
        "test",
        "test",
        "{}",
        "",
        "RUNNING",
        StreamError("", "", ""),
    ).to_dict()
    arcane_adapter = requests_mock.Adapter()
    arcane_adapter.register_uri(
        requests_mock.ANY,
        "https://arcane.example.com/v2/stream/info/STREAM_SOURCE/streamId",
        response_list=[
            {"json": mock_stream, "status_code": 200},
            {"text": "", "status_code": 401},
            {"json": mock_stream, "status_code": 200},
            {"text": "", "status_code": 401},
            {"json": mock_stream, "status_code": 200},
            {"json": mock_stream, "status_code": 200},
        ],
    )
    arcane_session = requests.Session()
    arcane_session.mount("https://", arcane_adapter)
    return arcane_session
