import json
import pathlib

import pytest

from esd_services_api_client.beast import JobRequest, JobSize, SubmissionMode


def test_request_ser():
    test_data_path = f"{pathlib.Path(__file__).parent.resolve()}/beast/job_request.json"
    with open(test_data_path, 'r', encoding='utf-8') as jr_ser_handle:
        jr_ser = jr_ser_handle.read()
        jr_dict = JobRequest.from_json(jr_ser, infer_missing=True).to_dict()
        assert {k: v for k, v in jr_dict.items() if v is not None} == json.loads(jr_ser)


@pytest.mark.parametrize("job_request", [
    (JobRequest(
        root_path='121',
        project_name='123',
        version='123213',
        runnable='1231',
        job_size=JobSize.SMALL,
        inputs=[],
        outputs=[],
        client_tag='12312',
        cost_optimized=True,
        overwrite=False,
        extra_args={},
        execution_group=None,
        flexible_driver=True,
        max_runtime_hours=None,
        runtime_tags=None,
        debug_mode=None,
        expected_parallelism=None,
        submission_mode=SubmissionMode.SWARM
    )),
    (JobRequest(
        root_path='121',
        project_name='123',
        version='123213',
        runnable='1231',
        job_size=None,
        inputs=[],
        outputs=[],
        client_tag='12312',
        cost_optimized=True,
        overwrite=False,
        extra_args={},
        execution_group=None,
        flexible_driver=True,
        max_runtime_hours=None,
        runtime_tags=None,
        debug_mode=None,
        expected_parallelism=None,
        submission_mode=SubmissionMode.SWARM
    )),
    (JobRequest(
        root_path='121',
        project_name='123',
        version='123213',
        runnable='1231',
        job_size=None,
        inputs=[],
        outputs=[],
        client_tag='12312',
        cost_optimized=True,
        overwrite=False,
        extra_args={},
        execution_group=None,
        flexible_driver=True,
        max_runtime_hours=None,
        runtime_tags=None,
        debug_mode=None,
        expected_parallelism=None,
        submission_mode=None
    ))
])
def test_request_dict(job_request):
    assert job_request.to_dict()
