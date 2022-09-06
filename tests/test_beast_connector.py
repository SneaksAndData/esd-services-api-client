import json
import pathlib

from esd_services_api_client.beast import JobRequest


def test_request_ser():
    test_data_path = f"{pathlib.Path(__file__).parent.resolve()}/beast/job_request.json"
    with open(test_data_path, 'r', encoding='utf-8') as jr_ser_handle:
        jr_ser = jr_ser_handle.read()
        try:
            jr_dict = JobRequest.from_json(jr_ser, infer_missing=True).to_dict()
            assert { k: v for k, v in jr_dict.items() if v is not None } == json.loads(jr_ser)
        except Exception as ex:
            print(ex)
            assert False
