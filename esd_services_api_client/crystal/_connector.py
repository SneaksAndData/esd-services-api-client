"""
  Connector for Crystal Job Runtime (AKS)
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

import json
from argparse import Namespace, ArgumentParser
from datetime import timedelta
from typing import Dict, Optional, Type, TypeVar, List

from adapta.logs import SemanticLogger
from adapta.storage.models.format import SerializationFormat
from adapta.utils import session_with_retries
from requests.auth import AuthBase

from esd_services_api_client.boxer import BoxerTokenAuth
from esd_services_api_client.crystal._api_versions import ApiVersion
from esd_services_api_client.crystal._models import (
    RequestResult,
    AlgorithmRunResult,
    CrystalEntrypointArguments,
    AlgorithmRequest,
    AlgorithmConfiguration,
)

T = TypeVar("T")  # pylint: disable=C0103


def add_crystal_args(parser: Optional[ArgumentParser] = None) -> ArgumentParser:
    """
    Add Crystal arguments to the command line argument parser.
    Notice that you need to add these arguments before calling `parse_args`.
    If no parser is provided, a new will be instantiated.

    :param parser: Existing argument parser.
    :return: The existing argument parser (if provided) with Crystal arguments added.
    """
    if parser is None:
        parser = ArgumentParser()

    parser.add_argument(
        "--sas-uri", required=True, type=str, help="SAS URI for input data"
    )
    parser.add_argument("--request-id", required=True, type=str, help="ID of the task")
    parser.add_argument(
        "--sign-result", dest="sign_result", required=False, action="store_true"
    )
    parser.set_defaults(sign_result=False)

    return parser


def extract_crystal_args(args: Namespace) -> CrystalEntrypointArguments:
    """
    Extracts parsed Crystal arguments and returns as a dataclass.
    :param args: Parsed arguments.
    :return: CrystalArguments object
    """
    return CrystalEntrypointArguments(
        sas_uri=args.sas_uri, request_id=args.request_id, sign_result=args.sign_result
    )


class CrystalConnector:
    """
    Crystal API connector
    """

    def __init__(
        self,
        *,
        base_url: str,
        logger: Optional[SemanticLogger] = None,
        auth: Optional[AuthBase] = None,
        api_version: ApiVersion = ApiVersion.V1_2,
        default_timeout: timedelta = timedelta(seconds=300),
        default_retry_count: int = 10,
    ):
        self.base_url = base_url
        self.http = session_with_retries(
            status_list=(400, 429, 500, 502, 503, 504, 404),
            retry_count=default_retry_count,
            request_timeout=default_timeout.total_seconds(),
        )
        self._api_version = api_version
        self._logger = logger
        if isinstance(auth, BoxerTokenAuth):
            assert (
                api_version == ApiVersion.V1_2
            ), "Cannot use BoxerTokenAuth with Crystal API versions prior to 1.2."

        self.http.auth = auth

    @classmethod
    def create_anonymous(
        cls,
        base_url: str,
        logger: Optional[SemanticLogger] = None,
        api_version: ApiVersion = ApiVersion.V1_2,
    ) -> "CrystalConnector":
        """Creates Crystal connector with no authentication.
        This should be use for accessing Crystal from inside a hosting cluster."""
        return cls(base_url=base_url, logger=logger, api_version=api_version)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def create_run(
        self,
        algorithm: str,
        payload: Dict,
        custom_config: Optional[AlgorithmConfiguration] = None,
        tag: Optional[str] = None,
    ) -> str:
        """
          Creates a Crystal job run against the latest API version.

        :param algorithm: Name of a connected algorithm.
        :param payload: Algorithm payload.
        :param custom_config: Customized config for this run.
        :param tag: Client-side submission identifier.
        :return: Request identifier assigned to the job by Crystal.
        """

        def get_api_path() -> str:
            if self._api_version == ApiVersion.V1_2:
                return f"{self.base_url}/algorithm/{self._api_version.value}/run/{algorithm}"

            raise ValueError(f"Unsupported API version {self._api_version}")

        run_body = AlgorithmRequest(
            algorithm_name=algorithm,
            algorithm_parameters=payload,
            custom_configuration=custom_config,
            tag=tag,
        ).to_dict()

        run_response = self.http.post(get_api_path(), json=run_body)

        # raise if not successful
        run_response.raise_for_status()

        run_id = run_response.json()["requestId"]

        if self._logger:
            self._logger.debug(
                "Run initiated for algorithm {algorithm}: {run_id}",
                algorithm=algorithm,
                run_id=run_id,
            )

        return run_id

    def retrieve_run(
        self, run_id: str, algorithm: Optional[str] = None
    ) -> RequestResult:
        """
        Retrieves a submitted Crystal job.

        :param run_id: Request identifier assigned to the job by Crystal.
        :param algorithm: Name of an algorithm.
        """

        def get_api_path() -> str:
            if self._api_version == ApiVersion.V1_2:
                return f"{self.base_url}/algorithm/{self._api_version.value}/results/{algorithm}/requests/{run_id}"

            raise ValueError(f"Unsupported API version {self._api_version}")

        response = self.http.get(url=get_api_path())

        # raise if not successful
        response.raise_for_status()

        crystal_result = RequestResult.from_dict(response.json())

        return crystal_result

    def retrieve_runs(
        self, tag: str, algorithm: Optional[str] = None
    ) -> List[RequestResult]:
        """
        Retrieves all submitted Crystal jobs with matching tags.

        :param tag: A request tag assigned by a client.
        :param algorithm: Name of an algorithm.
        """

        def get_api_path() -> str:
            if self._api_version == ApiVersion.V1_2:
                return f"{self.base_url}/algorithm/{self._api_version.value}/results/{algorithm}/tags/{tag}"

            raise ValueError(f"Unsupported API version {self._api_version}")

        response = self.http.get(url=get_api_path())

        # raise if not successful
        response.raise_for_status()

        return [RequestResult.from_dict(run_result) for run_result in response.json()]

    def submit_result(
        self,
        result: AlgorithmRunResult,
        run_id: str,
        algorithm: Optional[str] = None,
        debug: bool = False,
    ) -> None:
        """
        Submit a result of an algorithm back to Crystal.
        Notice, this method is only intended to be used within Crystal, as it doesn't use authentication.

        :param result: The result of the algorithm.
        :param algorithm: Name of a connected algorithm.
        :param run_id: Request identifier assigned to the job by Crystal.
        :param debug: If True, print the submission URL and body, but do not send the http request.
        """

        def get_api_path() -> str:
            if self._api_version == ApiVersion.V1_2:
                return f"{self.base_url}/algorithm/{self._api_version.value}/complete/{algorithm}/requests/{run_id}"

            raise ValueError(f"Unsupported API version {self._api_version}")

        payload = {
            "cause": result.cause,
            "message": result.message,
            "sasUri": result.sas_uri,
        }

        if debug and self._logger is not None:
            self._logger.debug(
                "Submitting result to {submission_url}, payload {payload}",
                submission_url=get_api_path(),
                payload=json.dumps(payload),
            )

        else:
            run_response = self.http.post(url=get_api_path(), json=payload)

            # raise if not successful
            run_response.raise_for_status()

    @staticmethod
    def read_input(
        *,
        crystal_arguments: CrystalEntrypointArguments,
        serialization_format: Type[SerializationFormat[T]],
    ) -> T:
        """
        Read Crystal input given in the SAS URI provided in the CrystalEntrypointArguments
        :param crystal_arguments: The arguments given to the Crystal job.
        :param serialization_format: The format used to deserialize the contents of the SAS URI.
        :return: The deserialized input data.
        """
        http_session = session_with_retries()
        http_response = http_session.get(url=crystal_arguments.sas_uri)
        http_response.raise_for_status()
        http_session.close()
        return serialization_format().deserialize(http_response.content)

    def dispose(self) -> None:
        """
        Gracefully dispose object.
        """
        self.http.close()
