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

import pytest
from typing import Type
import pandas
import requests.exceptions
from adapta.storage.models.format import (
    DictJsonSerializationFormat,
    SerializationFormat,
    DataFrameParquetSerializationFormat,
    DataFrameJsonSerializationFormat,
)

from esd_services_api_client.boxer import (
    ExternalTokenAuth,
    BoxerConnector,
    BoxerTokenAuth,
    RefreshableExternalTokenAuth,
)
from esd_services_api_client.crystal import (
    CrystalConnector,
    CrystalEntrypointArguments,
    RequestLifeCycleStage,
    RequestResult,
)
import responses


class MockHttpResponse:
    def __init__(self, data: any):
        self.content = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.content


class MockHttpConnection:
    def __init__(self, response: MockHttpResponse):
        self.response = response

    def get(self, *args: any, **kwargs: any):
        return self.response

    def close(self):
        pass


@pytest.mark.parametrize(
    "serializer, data",
    [
        (DictJsonSerializationFormat, {"test": "test"}),
        (
            DataFrameParquetSerializationFormat,
            pandas.DataFrame(data={"test": [1, 2, 3]}),
        ),
        (DataFrameJsonSerializationFormat, pandas.DataFrame(data={"test": [1, 2, 3]})),
    ],
)
def test_crystal_read_input(mocker, serializer: Type[SerializationFormat], data: any):
    """
    Test that the function `read_input` in the `CrystalConnector` object deserializes and returns the correct data.
    """
    mocker.patch(
        "esd_services_api_client.crystal._connector.session_with_retries",
        return_value=MockHttpConnection(MockHttpResponse(serializer().serialize(data))),
    )

    args = CrystalEntrypointArguments(
        sas_uri="https://some.sas.url.com", request_id="test-id"
    )

    read_data = CrystalConnector.read_input(
        crystal_arguments=args, serialization_format=serializer
    )

    if isinstance(data, pandas.DataFrame):
        assert data.equals(read_data)
    else:
        assert data == read_data


@pytest.mark.parametrize(
    "request_statuses",
    [
        [
            RequestLifeCycleStage.RUNNING,
            RequestLifeCycleStage.RUNNING,
            RequestLifeCycleStage.COMPLETED,
        ],
        [
            RequestLifeCycleStage.COMPLETED,
        ],
        [
            RequestLifeCycleStage.NEW,
            RequestLifeCycleStage.BUFFERED,
            RequestLifeCycleStage.THROTTLED,
            RequestLifeCycleStage.FAILED,
        ],
        [
            RequestLifeCycleStage.FAILED,
        ],
        [
            RequestLifeCycleStage.SCHEDULING_TIMEOUT,
        ],
        [
            RequestLifeCycleStage.DEADLINE_EXCEEDED,
        ],
    ],
)
def test_await_runs_request_id(mocker, request_statuses):
    request_id = "some_request_id"

    mocker.patch(
        "esd_services_api_client.crystal._connector.session_with_retries",
        return_value=MockHttpConnection(MockHttpResponse({"run_id": request_id})),
    )
    connector = CrystalConnector.create_anonymous(base_url="https://some.url.com")

    request_results = [
        RequestResult(run_id=request_id, status=status) for status in request_statuses
    ]

    connector._retrieve_run = mocker.Mock(side_effect=request_results)

    result = connector.await_runs(run_ids=[request_id], algorithm="some_algorithm")[
        request_id
    ]
    expected_result = request_results[-1]

    assert result == expected_result


@responses.activate
@pytest.mark.timeout(60)
def test_boxer_token_refresh():
    """
    Check that BoxerTokenAuth updates the boxer token if it's expired
    """
    method = test_external_token_refresh.__name__
    responses.add(
        responses.Response(method="GET", url=f"https://example.com/token/{method}")
    )
    __mock_crystal_responses()

    external_auth = ExternalTokenAuth("external_token", method)
    boxer_connector = BoxerConnector(base_url="https://example.com", auth=external_auth)
    connector = CrystalConnector(
        base_url="https://example.com", auth=BoxerTokenAuth(boxer_connector)
    )
    connector.await_runs("algorithm", ["id"])


@responses.activate
@pytest.mark.timeout(60)
def test_external_token_refresh():
    """
    Check that RefreshableExternalTokenAuth updates the external token if it's expired
    """
    method = test_external_token_refresh.__name__
    responses.add(
        responses.Response(
            method="GET", url=f"https://example.com/token/{method}", body="token1"
        )
    )
    responses.add(
        responses.Response(
            method="GET", url=f"https://example.com/token/{method}", status=401
        )
    )
    responses.add(
        responses.Response(
            method="GET", url=f"https://example.com/token/{method}", body="token2"
        )
    )
    __mock_crystal_responses()

    external_auth = RefreshableExternalTokenAuth(lambda: "external_token", method)
    boxer_connector = BoxerConnector(base_url="https://example.com", auth=external_auth)
    connector = CrystalConnector(
        base_url="https://example.com", auth=BoxerTokenAuth(boxer_connector)
    )
    connector.await_runs("algorithm", ["id"])


@responses.activate
@pytest.mark.timeout(60)
def test_external_token_refresh_failed():
    """
    Check that RefreshableExternalTokenAuth will not cause infinite loop if got 401 after external token update
    """
    method = test_external_token_refresh_failed.__name__
    responses.add(
        responses.Response(
            method="GET", url=f"https://example.com/token/{method}", body="token1"
        )
    )
    responses.add(
        responses.Response(
            method="GET", url=f"https://example.com/token/{method}", status=401
        )
    )
    responses.add(
        responses.Response(
            method="GET", url=f"https://example.com/token/{method}", status=401
        )
    )
    responses.add(
        responses.Response(
            method="GET", url=f"https://example.com/token/{method}", status=401
        )
    )
    __mock_crystal_responses()

    external_auth = RefreshableExternalTokenAuth(lambda: "external_token", method)
    boxer_connector = BoxerConnector(base_url="https://example.com", auth=external_auth)
    connector = CrystalConnector(
        base_url="https://example.com", auth=BoxerTokenAuth(boxer_connector)
    )
    with pytest.raises(requests.exceptions.HTTPError) as error:
        connector.await_runs("algorithm", ["id"])
    assert error.value.response.status_code == requests.codes["unauthorized"]


def __make_response(status: int, lifecycle_stage: RequestLifeCycleStage):
    resp = responses.Response(
        method="GET",
        url="https://example.com/algorithm/v1.2/results/algorithm/requests/id",
        json=RequestResult("id", lifecycle_stage, None, None).to_dict(),
    )
    resp.status = status
    return resp


def __mock_crystal_responses():
    responses.add(__make_response(200, RequestLifeCycleStage.RUNNING))
    responses.add(__make_response(401, RequestLifeCycleStage.RUNNING))
    responses.add(__make_response(200, RequestLifeCycleStage.RUNNING))
    responses.add(__make_response(200, RequestLifeCycleStage.COMPLETED))
