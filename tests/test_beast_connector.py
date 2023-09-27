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

import json
import pathlib

import pytest

from esd_services_api_client.beast import JobRequest


def test_request_ser():
    test_data_path = f"{pathlib.Path(__file__).parent.resolve()}/beast/job_request.json"
    with open(test_data_path, "r", encoding="utf-8") as jr_ser_handle:
        jr_ser = jr_ser_handle.read()
        jr_dict = JobRequest.from_json(jr_ser, infer_missing=True).to_dict()
        assert {k: v for k, v in jr_dict.items() if v is not None} == json.loads(jr_ser)


@pytest.mark.parametrize(
    "job_request",
    [
        (
            JobRequest(
                inputs=[],
                outputs=[],
                client_tag="12312",
                overwrite=False,
                extra_args={},
            )
        ),
        (
            JobRequest(
                inputs=[],
                outputs=[],
                client_tag="12312",
                overwrite=False,
                extra_args={},
            )
        ),
        (
            JobRequest(
                inputs=[],
                outputs=[],
                client_tag="12312",
                overwrite=False,
                extra_args={},
            )
        ),
    ],
)
def test_request_dict(job_request):
    assert job_request.to_dict()
