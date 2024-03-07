"""
  Connector for Beast Workload Manager (Spark AKS)
"""
#  Copyright (c) 2023-2024. ECCO Sneaks & Data
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
from http.client import HTTPException
from json import JSONDecodeError
from typing import Optional, Any

import backoff
from adapta.utils import doze, session_with_retries
from urllib3.exceptions import ProtocolError, HTTPError

from esd_services_api_client.beast.v3._models import (
    JobRequest,
    BeastJobParams,
    SparkSubmissionConfiguration,
)
from esd_services_api_client.boxer import BoxerTokenAuth


class BeastConnector:
    """
    Beast API connector
    """

    def __init__(
        self,
        *,
        base_url,
        code_root="/ecco/dist",
        lifecycle_check_interval: int = 60,
        auth: Optional[BoxerTokenAuth] = None,
        failure_type: Optional[Exception] = None,
    ):
        """
          Creates a Beast connector, capable of submitting/status tracking etc.

        :param base_url: Base URL for Beast Workload Manager.
        :param code_root: Root folder for code deployments.
        :param auth: Boxer-based authentication
        :param lifecycle_check_interval: Time to wait between lifecycle checks for submissions/cancellations etc.
        """
        self.base_url = base_url
        self.code_root = code_root
        self.lifecycle_check_interval = lifecycle_check_interval
        self.failed_stages = [
            "FAILED",
            "SCHEDULING_FAILED",
            "RETRIES_EXCEEDED",
            "SUBMISSION_FAILED",
            "STALE",
        ]
        self.success_stages = ["COMPLETED"]
        self.http = session_with_retries()
        if auth and isinstance(auth, BoxerTokenAuth):
            self.http.hooks["response"].append(auth.get_refresh_hook(self.http))
        self.http.auth = auth
        self._failure_type = failure_type or Exception
        self._version = "v3"

    @property
    def version(self):
        """
        Returns the client API version for this connector
        """
        return self._version

    @classmethod
    def create_anonymous(
        cls,
        base_url,
        code_root="/ecco/dist",
        lifecycle_check_interval: int = 60,
        failure_type: Optional[Exception] = None,
    ) -> "BeastConnector":
        """Creates Beast connector with no authentication.
        This should be used within a hosting clusters."""
        return cls(
            base_url=base_url,
            code_root=code_root,
            lifecycle_check_interval=lifecycle_check_interval,
            failure_type=failure_type,
        )

    def _submit(self, request: JobRequest, spark_job_name: str) -> (str, str):
        request_json = request.to_dict()

        print(f"Submitting request: {json.dumps(request_json)}")

        submission_result = self.http.post(
            f"{self.base_url}/job/submit/{spark_job_name}", json=request_json
        )
        submission_json = submission_result.json()

        if submission_result.status_code == 202 and submission_json:
            print(
                f"Beast has accepted the request, stage: {submission_json['lifeCycleStage']}, id: {submission_json['id']}"
            )
        else:
            raise HTTPException(
                f"Error {submission_result.status_code} when submitting a request: {submission_result.text}"
            )

        return submission_json["id"], submission_json["lifeCycleStage"]

    @backoff.on_exception(
        wait_gen=backoff.expo,
        exception=(
            HTTPError,
            KeyError,
            JSONDecodeError,
            ProtocolError,
            ConnectionError,
            ConnectionRefusedError,
            ConnectionAbortedError,
            ConnectionResetError,
        ),
        max_time=300,
        raise_on_giveup=True,
    )
    def _existing_submission(
        self, submitted_tag: str
    ) -> (Optional[str], Optional[str]):
        print(f"Looking for existing submissions of {submitted_tag}")

        response = self.http.get(f"{self.base_url}/job/requests/tags/{submitted_tag}")
        response.raise_for_status()
        existing_submissions = response.json()

        if len(existing_submissions) == 0:
            print(f"No previous submissions found for {submitted_tag}")
            return None, None

        running_submissions = []
        for submission_request_id in existing_submissions:
            response = self.http.get(
                f"{self.base_url}/job/requests/{submission_request_id}"
            )
            response.raise_for_status()
            submission_lifecycle = response.json()["lifeCycleStage"]
            if (
                submission_lifecycle not in self.success_stages
                and submission_lifecycle not in self.failed_stages
            ):
                print(
                    f"Found a running submission of {submitted_tag}: {submission_request_id}."
                )
                running_submissions.append(
                    (submission_request_id, submission_lifecycle)
                )

        if len(running_submissions) == 0:
            print("None of found submissions are active")
            return None, None

        if len(running_submissions) == 1:
            return running_submissions[0][0], running_submissions[0][1]

        raise self._failure_type(
            f"Fatal: more than one submission of {submitted_tag} is running: {running_submissions}. Please review their status restart/terminate the task accordingly"
        )

    def run_job(self, job_params: BeastJobParams, job_name: str):
        """
          Runs a job through Beast

        :param job_params: Parameters for Beast Job body.
        :param job_name: Name of the SparkJob to invoke.
        :return: A JobRequest for Beast.
        """

        (request_id, request_lifecycle) = self._existing_submission(
            submitted_tag=job_params.client_tag
        )

        if request_id:
            print(f"Resuming watch for {request_id}")

        if not request_id:
            prepared_arguments = {
                key: str(value) for (key, value) in job_params.extra_arguments.items()
            }

            submit_request = JobRequest(
                inputs=job_params.project_inputs,
                outputs=job_params.project_outputs,
                extra_args=prepared_arguments,
                client_tag=job_params.client_tag,
                expected_parallelism=job_params.expected_parallelism,
            )

            (request_id, request_lifecycle) = self._submit(submit_request, job_name)

        while (
            request_lifecycle not in self.success_stages
            and request_lifecycle not in self.failed_stages
        ):
            doze(self.lifecycle_check_interval)
            request_lifecycle = self.get_request_lifecycle_stage(request_id)
            print(f"Request: {request_id}, current state: {request_lifecycle}")

        if request_lifecycle in self.failed_stages:
            raise self._failure_type(
                f"Execution failed, please find request's log at: {self.base_url}/job/logs/{request_id}"
            )

    @staticmethod
    def _report_backoff_failure(
        target: Any, args: Any, kwargs: Any, tries: int, elapsed: int, wait: int, **_
    ) -> None:
        print(
            f"Retry with back off {wait:0.1f} seconds after {elapsed} seconds ({tries} tries), calling function {target} with args {args} and kwargs {kwargs}"
        )

    @backoff.on_exception(
        wait_gen=backoff.expo,
        exception=(
            HTTPError,
            KeyError,
            JSONDecodeError,
            ProtocolError,
            ConnectionError,
            ConnectionRefusedError,
            ConnectionAbortedError,
            ConnectionResetError,
        ),
        max_time=300,
        raise_on_giveup=False,
        on_giveup=_report_backoff_failure,
    )
    def get_request_lifecycle_stage(self, request_id: str) -> Optional[str]:
        """
          Returns a lifecycle stage for the given request. Returns None in case error retry fails to resolve within given timeout.
        :param request_id: A request identifier to read lifecycle stage for.
        """
        response = self.http.get(f"{self.base_url}/job/requests/{request_id}")
        response.raise_for_status()

        return response.json()["lifeCycleStage"]

    def get_request_runtime_info(self, request_id: str) -> Optional[dict]:
        """
          Returns the runtime information for the given request. Returns None in case error retry fails to resolve within given timeout.
        :param request_id: A request identifier to read runtime info for.
        """
        response = self.http.get(f"{self.base_url}/job/requests/{request_id}")
        response.raise_for_status()

        return response.json()

    def start_job(self, job_params: BeastJobParams, job_name: str) -> Optional[str]:
        """
          Starts a job through Beast.

        :param job_params: Parameters for Beast Job body.
        :param job_name: Name of the SparkJob to invoke.
        :return: A JobRequest for Beast.
        """

        (request_id, _) = self._existing_submission(submitted_tag=job_params.client_tag)

        if not request_id:
            prepared_arguments = {
                key: str(value) for (key, value) in job_params.extra_arguments.items()
            }

            submit_request = JobRequest(
                inputs=job_params.project_inputs,
                outputs=job_params.project_outputs,
                extra_args=prepared_arguments,
                client_tag=job_params.client_tag,
                expected_parallelism=job_params.expected_parallelism,
            )

            request_id, _ = self._submit(submit_request, job_name)

        return request_id

    def get_configuration(
        self, configuration_name: str
    ) -> Optional[SparkSubmissionConfiguration]:
        """
          Returns a deployed SparkJob configuration.
        :param configuration_name: Name of the configuration to find
        :return: A SparkSubmissionConfiguration object, if found, or None
        """
        response = self.http.get(f"{self.base_url}/job/deployed/{configuration_name}")
        if response.status_code == 404:
            return None
        if not response.ok:
            response.raise_for_status()

        return SparkSubmissionConfiguration.from_dict(response.json())

    def get_logs(self, request_id: str) -> Optional[str]:
        """
          Returns logs for a running or a completed submission.

        :param request_id: Submission request identifier.
        :return: A job log, if found, or None
        """
        response = self.http.get(f"{self.base_url}/job/logs/{request_id}")
        if response.status_code == 404:
            return None
        if not response.ok:
            response.raise_for_status()

        return "\n".join(response.json())
