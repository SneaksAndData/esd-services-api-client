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

import copy

import pytest

from esd_services_api_client.beast import JobSocket


def _assert_socket_is_equal(socket_1: JobSocket, socket_2: JobSocket):
    assert socket_1.alias == socket_2.alias
    assert socket_1.data_path == socket_2.data_path
    assert socket_1.data_format == socket_2.data_format
    assert isinstance(socket_1, JobSocket)
    assert isinstance(socket_2, JobSocket)


def test_job_socket_serialization():
    socket = JobSocket(alias="foo", data_path="bar", data_format="baz")
    socket_deserialized = JobSocket.deserialize(socket.serialize())

    _assert_socket_is_equal(socket, socket_deserialized)


def test_socket_from_list():

    foo_socket = JobSocket(alias="foo", data_path="foo_path", data_format="foo_format")
    bar_socket = JobSocket(alias="bar", data_path="bar_path", data_format="bar_format")
    baz_socket = JobSocket(alias="baz", data_path="baz_path", data_format="baz_format")
    sockets = [foo_socket, bar_socket, baz_socket]

    _assert_socket_is_equal(foo_socket, JobSocket.from_list(sockets, "foo"))
    _assert_socket_is_equal(bar_socket, JobSocket.from_list(sockets, "bar"))
    _assert_socket_is_equal(baz_socket, JobSocket.from_list(sockets, "baz"))

    sockets.append(copy.deepcopy(foo_socket))
    with pytest.raises(ValueError):
        JobSocket.from_list(sockets, "foo")

    with pytest.raises(ValueError):
        JobSocket.from_list(sockets, "non-existing")
