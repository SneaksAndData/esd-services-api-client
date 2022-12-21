from unittest.mock import Mock, MagicMock

import requests

from esd_services_api_client.arcane import ArcaneConnector, StreamInfo, StreamError
from esd_services_api_client.boxer import BoxerConnector, BoxerTokenAuth, ExternalTokenAuth
import requests_mock


def test_retries():
    arcane_adapter = requests_mock.Adapter()
    boxer_adapter = requests_mock.Adapter()
    boxer_adapter.register_uri(
        requests_mock.ANY,
        "https://boxer.example.com/token/test",
        json={}
    )

    mock_stream = StreamInfo('id', 'STREAM_SOURCE', "", "test", "test", "{}", "", "RUNNING", StreamError("", "", "")).to_dict()
    arcane_adapter.register_uri(
        requests_mock.ANY,
        "https://arcane.example.com/stream/info/STREAM_SOURCE/streamId",
        response_list=[
            {"json": mock_stream, "status_code": 200},
            {"text": "", "status_code": 401},
            {"json": mock_stream, "status_code": 200},
            {"text": "", "status_code": 403},
            {"json": mock_stream, "status_code": 200},
            {"json": mock_stream, "status_code": 200},
        ]
    )
    arcane_session = requests.Session()
    arcane_session.mount("https://", arcane_adapter)

    boxer_session = requests.Session()
    boxer_session.mount("https://", boxer_adapter)

    external_token_auth = ExternalTokenAuth(token="token", policy="test")
    boxer_connector = BoxerConnector(base_url="https://boxer.example.com", auth=external_token_auth, session=boxer_session)
    boxer_auth = BoxerTokenAuth(boxer_connector)

    arcane_connector = ArcaneConnector(base_url="https://arcane.example.com", auth=boxer_auth, session=arcane_session)
    streams = []
    for _ in range(0, 5):
        streams.append(arcane_connector.get_stream("STREAM_SOURCE", "streamId"))

    assert len(streams) == 5
    assert len(boxer_adapter.request_history) == 3
