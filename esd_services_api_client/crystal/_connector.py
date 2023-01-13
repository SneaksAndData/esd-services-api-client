"""
  Connector for Crystal Job Runtime (AKS)
"""
import os
from argparse import Namespace, ArgumentParser
from typing import Dict, Optional, Type, TypeVar, List

from proteus.storage.models.format import SerializationFormat
from proteus.utils import session_with_retries
from requests.auth import HTTPBasicAuth, AuthBase

from esd_services_api_client.boxer import BoxerTokenAuth
from esd_services_api_client.crystal._api_versions import ApiVersion
from esd_services_api_client.crystal._models import RequestResult, AlgorithmRunResult, CrystalEntrypointArguments, \
    AlgorithmRequest, AlgorithmConfiguration

T = TypeVar('T')  # pylint: disable=C0103


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

    parser.add_argument('--sas-uri', required=True, type=str, help='SAS URI for input data')
    parser.add_argument('--request-id', required=True, type=str, help='ID of the task')
    parser.add_argument('--results-receiver', required=True, type=str,
                        help='HTTP(s) endpoint to which output SAS URI is passed')
    parser.add_argument('--results-receiver-user', required=False, type=str,
                        help='User for results receiver (authentication)')
    parser.add_argument('--results-receiver-password', required=False, type=str,
                        help='Password for results receiver (authentication)')
    parser.add_argument('--sign-result', dest='sign_result', required=False, action='store_true')
    parser.set_defaults(sign_result=False)

    return parser


def extract_crystal_args(args: Namespace) -> CrystalEntrypointArguments:
    """
    Extracts parsed Crystal arguments and returns as a dataclass.
    :param args: Parsed arguments.
    :return: CrystalArguments object
    """
    return CrystalEntrypointArguments(
        sas_uri=args.sas_uri,
        request_id=args.request_id,
        results_receiver=args.results_receiver,
        sign_result=args.sign_result
    )


class CrystalConnector:
    """
      Crystal API connector
    """

    def __init__(
            self, *,
            base_url: str,
            auth: Optional[AuthBase] = None,
            api_version: ApiVersion = ApiVersion.V1_1
    ):
        self.base_url = base_url
        self.http = session_with_retries()
        self._api_version = api_version

        if isinstance(auth, BoxerTokenAuth):
            assert api_version == ApiVersion.V1_2, 'Cannot use BoxerTokenAuth with version prior to 1.2.'

        if isinstance(auth, HTTPBasicAuth):
            assert api_version == ApiVersion.V1_1, 'Basic auth can only be used with versions prior to 1.2.'

        self.http.auth = auth

    @classmethod
    def create_authenticated(cls, base_url: str, user: Optional[str] = None, password: Optional[str] = None) -> 'CrystalConnector':
        """Creates Crystal connector with basic authentication.
        For connecting to Crystal outside the Crystal kubernetes cluster, e.g.
        from other cluster or Airflow environment.
        """
        return cls(
            base_url=base_url,
            auth=HTTPBasicAuth(user or os.environ.get('CRYSTAL_USER'), password or os.environ.get('CRYSTAL_PASSWORD'))
        )

    @classmethod
    def create_anonymous(cls, base_url: str) -> 'CrystalConnector':
        """Creates Crystal connector with no authentication.
         This should be use for accessing Crystal from inside a hosting cluster."""
        return cls(base_url=base_url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def create_run(
            self,
            algorithm: str,
            payload: Dict,
            custom_config: Optional[AlgorithmConfiguration] = None,
            tag: Optional[str] = None
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
            if self._api_version == ApiVersion.V1_1:
                return f"{self.base_url}/algorithm/{self._api_version.value}/run"
            if self._api_version == ApiVersion.V1_2:
                return f"{self.base_url}/algorithm/{self._api_version.value}/run/{algorithm}"

            raise ValueError(f'Unsupported API version {self._api_version}')

        run_body = AlgorithmRequest(
            algorithm_name=algorithm,
            algorithm_parameters=payload,
            custom_configuration=custom_config,
            tag=tag
        ).to_dict()

        #print(f"Sending the following configuration for algorithm {algorithm}: {run_body}")

        run_response = self.http.post(get_api_path(), json=run_body)

        # raise if not successful
        run_response.raise_for_status()

        run_id = run_response.json()['requestId']

        #print(
         #   f"Algorithm run initiated: {run_id}. Check status at {self.base_url}/algorithm/{api_version}/run/{run_id}/result")

        return run_id

    def retrieve_run(self, run_id: str, algorithm: Optional[str] = None) -> RequestResult:
        """
        Retrieves a submitted Crystal job.

        :param run_id: Request identifier assigned to the job by Crystal.
        :param algorithm: Name of a connected algorithm.
        """
        def get_api_path() -> str:
            if self._api_version == ApiVersion.V1_1:
                return f'{self.base_url}/algorithm/{self._api_version.value}/run/{run_id}/result'
            if self._api_version == ApiVersion.V1_2:
                return f'{self.base_url}/algorithm/{self._api_version.value}/results/{algorithm}/requests/{run_id}'

            raise ValueError(f'Unsupported API version {self._api_version}')

        response = self.http.get(url=get_api_path())

        # raise if not successful
        response.raise_for_status()

        crystal_result = RequestResult.from_dict(response.json())

        return crystal_result

    def retrieve_runs(self, tag: str, algorithm: Optional[str] = None) -> List[RequestResult]:
        """
          Retrieves all submitted Crystal jobs with matching tags.

          :param tag: A request tag assigned by a client.
          :param algorithm: Name of a connected algorithm.
        """
        def get_api_path() -> str:
            if self._api_version == ApiVersion.V1_1:
                return f'{self.base_url}/algorithm/{self._api_version.value}/tag/{tag}/results'
            if self._api_version == ApiVersion.V1_2:
                return f'{self.base_url}/algorithm/{self._api_version.value}/results/{algorithm}/tags/{tag}'

            raise ValueError(f'Unsupported API version {self._api_version}')

        response = self.http.get(url=get_api_path())

        # raise if not successful
        response.raise_for_status()

        return [RequestResult.from_dict(run_result) for run_result in response.json()]

    def submit_result(self, result: AlgorithmRunResult, run_id: str, algorithm: Optional[str] = None, submit_base_url: Optional[str] = None) -> None:
        """
        Submit a result of an algorithm back to Crystal.
        Notice, this method is only intended to be used within Crystal, as it doesn't use authentication.

        :param result: The result of the algorithm.
        :param algorithm: Name of a connected algorithm.
        :param run_id: Request identifier assigned to the job by Crystal.
        :param: submit_base_url: Internal Crystal url to submit results to.
        """
        def get_api_path() -> str:
            if self._api_version == ApiVersion.V1_1:
                return f'{submit_base_url or self.base_url}/algorithm/{self._api_version.value}/run/complete'
            if self._api_version == ApiVersion.V1_2:
                return f'{submit_base_url or self.base_url}/algorithm/{self._api_version.value}/complete/{algorithm}/requests/{run_id}'

            raise ValueError(f'Unsupported API version {self._api_version}')

        payload = {
            'cause': result.cause,
            'message': result.message,
            'sasUri': result.sas_uri,
        }

        if self._api_version == ApiVersion.V1_1:
            payload['requestId'] = result.run_id

        run_response = self.http.post(
            url=get_api_path(),
            json=payload
        )

        # raise if not successful
        run_response.raise_for_status()

    @staticmethod
    def read_input(
            *,
            crystal_arguments: CrystalEntrypointArguments,
            serialization_format: Type[SerializationFormat[T]]
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
