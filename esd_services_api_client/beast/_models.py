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
from typing import List, Dict, Union
from warnings import warn

from cryptography.fernet import Fernet
from dataclasses_json import dataclass_json, LetterCase, DataClassJsonMixin


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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class JobRequest(DataClassJsonMixin):
    """
    Request body for a Beast submission
    """

    inputs: List[JobSocket]
    outputs: List[JobSocket]
    overwrite: bool
    extra_args: Dict[str, str]
    client_tag: str


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

    extra_arguments: Dict[str, Union[ArgumentValue, str]] = field(
        metadata={
            "description": "Extra arguments for a submission, defined by an author."
        }
    )
    client_tag: str = field(
        metadata={"description": "Client-assigned identifier for this request"}
    )
    project_inputs: List[JobSocket] = field(
        metadata={"description": "List of job inputs."}, default=list
    )
    project_outputs: List[JobSocket] = field(
        metadata={"description": "List of job outputs."}, default=list
    )
    overwrite_outputs: bool = field(
        metadata={
            "description": "Whether to wipe existing data before writing new out."
        },
        default=False,
    )
