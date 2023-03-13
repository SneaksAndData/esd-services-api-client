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
from adapta.storage.models.format import (
    DictJsonSerializationFormat,
    SerializationFormat,
    DataFrameParquetSerializationFormat,
    DataFrameJsonSerializationFormat,
)
from esd_services_api_client.crystal import CrystalConnector, CrystalEntrypointArguments


class MockHttpResponse:
    def __init__(self, data: bytes):
        self.content = data

    def raise_for_status(self):
        pass


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
