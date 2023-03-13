"""
  Models for Beast connector
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

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Union
from warnings import warn

from cryptography.fernet import Fernet
from dataclasses_json import dataclass_json, LetterCase, DataClassJsonMixin, config


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RequestDebugMode(DataClassJsonMixin):
    """
    Debug mode parameters for the request.
    """

    event_log_location: str
    max_size_per_file: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class JobSocket(DataClassJsonMixin):
    """
    Input/Output data map

    Attributes:
        alias: mapping key to be used by a consumer
        data_path: fully qualified path to actual data, i.e. abfss://..., s3://... etc.
        data_format: data format, i.e. csv, json, delta etc.
    """

    alias: str
    data_path: str
    data_format: str

    def to_utils_format(self) -> str:
        """Serializes JobSocket to string"""
        warn(
            "This method is deprecated. Use serialize method instead",
            DeprecationWarning,
        )
        return self.serialize()

    def serialize(self) -> str:
        """Serializes JobSocket to string"""
        return f"{self.alias}|{self.data_path}|{self.data_format}"

    @classmethod
    def deserialize(cls, job_socket: str) -> "JobSocket":
        """Deserializes JobSocket from string"""
        vals = job_socket.split("|")
        return cls(alias=vals[0], data_path=vals[1], data_format=vals[2])

    @staticmethod
    def from_list(sockets: List["JobSocket"], alias: str) -> "JobSocket":
        """Fetches a job socket from list of sockets.
        :param sockets: List of sockets
        :param alias: Alias to look up

        :returns: Socket with alias 'alias'
        """
        socket = [s for s in sockets if s.alias == alias]

        if len(socket) > 1:
            raise ValueError(f"Multiple job sockets exist with alias {alias}")
        if len(socket) == 0:
            raise ValueError(f"No job sockets exist with alias {alias}")
        return socket[0]


class JobSize(Enum):
    """
    Job size hints for Beast.

    TINY - jobs running DDL or hive imports or any tiny workload. Should receive minimum allowed resources (1 core, 1g ram per executor)
    SMALL - small workloads, one or 30% pod cores, 30% pod memory per executor
    MEDIUM - medium workloads, one or 30% pod cores, 50% pod memory per executor
    LARGE - large workloads, one or 30% pod cores, all available executor memory
    XLARGE - extra large workload, two or 60% pod cores, all available executor memory
    XXLARGE - x-extra large workloads, all available cores, all available memory
    """

    TINY = "TINY"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    XLARGE = "XLARGE"
    XXLARGE = "XXLARGE"


class SubmissionMode(Enum):
    """
    Submission modes supported by Beast.

    SWARM - submit a job to a shared cluster.
    K8S - submit a job directly to k8s.
    STREAM - submit a job directly to a shared cluster bypassing application limit constraints.
    """

    SWARM = "SWARM"
    K8S = "K8S"
    STREAM = "STREAM"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class JobRequest(DataClassJsonMixin):
    """
    Request body for a Beast submission
    """

    root_path: str
    project_name: str
    version: str
    runnable: str
    inputs: List[JobSocket]
    outputs: List[JobSocket]
    overwrite: bool
    extra_args: Dict[str, str]
    client_tag: str
    job_size: Optional[JobSize] = field(
        metadata=config(encoder=lambda v: v.value if v else None, decoder=JobSize)
    )
    execution_group: Optional[str]
    flexible_driver: Optional[bool]
    max_runtime_hours: Optional[int]
    additional_driver_node_tolerations: Optional[Dict[str, str]]
    debug_mode: Optional[RequestDebugMode]
    expected_parallelism: Optional[int]
    submission_mode: Optional[SubmissionMode] = field(
        metadata=config(
            encoder=lambda v: v.value if v else None, decoder=SubmissionMode
        )
    )


class ArgumentValue:
    """
    Wrapper around job argument value. Supports fernet encryption.
    """

    def __init__(self, *, value: str, encrypt=False, quote=False, is_env=False):
        """
          Initializes a new ArgumentValue

        :param value: Plain text value.
        :param encrypt: If set to True, value will be replaced with a fernet-encrypted value.
        :param quote: Whether a value should be quoted when it is stringified.
        :param is_env: whether value should be derived from env instead, using value as var name.
        """
        self._is_env = is_env
        self._encrypt = encrypt
        self._quote = quote
        self._value = value

    @property
    def value(self):
        """
          Returns the wrapped value

        :return:
        """
        if self._is_env:
            result = os.getenv(self._value)
        else:
            result = self._value

        if self._encrypt:
            result = self._encrypt_value(result)

        return result

    @staticmethod
    def _encrypt_value(value: str) -> str:
        """
          Encrypts a provided string

        :param value: payload to decrypt
        :return: Encrypted payload
        """
        encryption_key = os.environ.get("RUNTIME_ENCRYPTION_KEY", None).encode("utf-8")

        if not encryption_key:
            raise ValueError(
                "Encryption key not found, but a value is set to be encrypted. Either disable encryption or map RUNTIME_ENCRYPTION_KEY on this container from airflow secrets."
            )

        fernet = Fernet(encryption_key)
        return fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def __str__(self):
        """
         Stringifies the value and optionally wraps it in quotes.

        :return:
        """
        if self._quote:
            return f"'{str(self.value)}'"

        return self.value


@dataclass
class BeastJobParams:
    """
    Parameters for Beast jobs.
    """

    project_name: str = field(
        metadata={
            "description": "Repository name that contains a runnable. Must be deployed to a Beast-managed cluster beforehand."
        }
    )
    project_version: str = field(
        metadata={"description": "Semantic version of a runnable."}
    )
    project_runnable: str = field(
        metadata={
            "description": "Path to a runnable, for example src/folder1/my_script.py."
        }
    )
    project_inputs: List[JobSocket] = field(
        metadata={"description": "List of job inputs."}
    )
    project_outputs: List[JobSocket] = field(
        metadata={"description": "List of job outputs."}
    )
    overwrite_outputs: bool = field(
        metadata={
            "description": "Whether to wipe existing data before writing new out."
        }
    )
    extra_arguments: Dict[str, Union[ArgumentValue, str]] = field(
        metadata={
            "description": "Extra arguments for a submission, defined by an author."
        }
    )
    client_tag: str = field(
        metadata={"description": "Client-assigned identifier for this request"}
    )
    size_hint: Optional[JobSize] = field(
        metadata={"description": "Job size hint for Beast."}, default=JobSize.SMALL
    )
    execution_group: Optional[str] = field(
        metadata={
            "description": "Spark scheduler pool that should be used for this request"
        },
        default=None,
    )
    flexible_driver: Optional[bool] = field(
        metadata={
            "description": "Whether to use fixed-size driver or derive driver memory from master node max memory."
        },
        default=False,
    )
    max_runtime_hours: Optional[int] = field(
        metadata={
            "description": "Sets maximum allowed job run duration. Server-side default is 12 hours"
        },
        default=None,
    )
    debug_mode: Optional[RequestDebugMode] = field(
        metadata={
            "description": "Enables saving Spark event log for later viewing through History Server"
        },
        default=None,
    )
    expected_parallelism: Optional[int] = field(
        metadata={
            "description": "Expected number of tasks per node. Lowering this setting increases number of nodes requested in K8S mode,"
        },
        default=None,
    )
    submission_mode: Optional[SubmissionMode] = field(
        metadata={
            "description": "Mode to submit a request in: shared cluster or direct k8s."
        },
        default=None,
    )
    additional_driver_node_tolerations: Optional[Dict[str, str]] = field(
        metadata={
            "description": "Additional taints allowed for application driver nodes."
        },
        default=None,
    )
