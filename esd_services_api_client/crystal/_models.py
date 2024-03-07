"""
  Models for Crystal connector
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

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from dataclasses_json import dataclass_json, LetterCase, DataClassJsonMixin, config


class RequestLifeCycleStage(Enum):
    """
    Crystal status states.
    """

    NEW = "NEW"
    BUFFERED = "BUFFERED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SCHEDULING_TIMEOUT = "SCHEDULING_TIMEOUT"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    THROTTLED = "THROTTLED"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RequestResult(DataClassJsonMixin):
    """
    The Crystal result when retrieving an existing run.
    """

    run_id: str = field(metadata=config(field_name="requestId"))
    status: RequestLifeCycleStage = field(
        metadata=config(
            encoder=lambda v: v.value if v else None, decoder=RequestLifeCycleStage
        ),
        default=None,
    )
    result_uri: Optional[str] = None
    run_error_message: Optional[str] = None


@dataclass
class AlgorithmRunResult:
    """
    The result of an algorithm to be submitted to Crystal.
    """

    run_id: Optional[str] = None
    cause: Optional[str] = None
    message: Optional[str] = None
    sas_uri: Optional[str] = None


@dataclass
class CrystalEntrypointArguments:
    """
    Holds Crystal arguments parsed from command line.
    """

    sas_uri: str
    request_id: str
    sign_result: Optional[bool] = None


class AlgorithmConfigurationValueType(Enum):
    """
    Value type for algorithm config maps and secrets.

    PLAIN - plain text value
    RELATIVE_REFERENCE - reference to a file deployed alongside algorithm config.
    """

    PLAIN = "PLAIN"
    RELATIVE_REFERENCE = "RELATIVE_REFERENCE"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AlgorithmConfigurationEntry(DataClassJsonMixin):
    """
    Crystal algorithm configuration entry.
    """

    name: str
    value: str
    value_type: Optional[AlgorithmConfigurationValueType] = field(
        metadata=config(
            encoder=lambda v: v.value if v else None,
            decoder=AlgorithmConfigurationValueType,
        ),
        default=None,
    )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AlgorithmConfiguration(DataClassJsonMixin):
    """
    Crystal algorithm configuration. Used for overriding defaults.
    """

    image_repository: Optional[str] = None
    image_tag: Optional[str] = None
    deadline_seconds: Optional[int] = None
    maximum_retries: Optional[int] = None
    env: Optional[List[AlgorithmConfigurationEntry]] = None
    secrets: Optional[List[str]] = None
    args: Optional[List[AlgorithmConfigurationEntry]] = None
    cpu_limit: Optional[str] = None
    memory_limit: Optional[str] = None
    workgroup: Optional[str] = None
    additional_workgroups: Optional[Dict[str, str]] = None
    version: Optional[str] = None
    monitoring_parameters: Optional[List[str]] = None
    custom_resources: Optional[Dict[str, str]] = None
    speculative_attempts: Optional[int] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AlgorithmRequest(DataClassJsonMixin):
    """
    Crystal algorthm request.
    """

    algorithm_parameters: Dict
    algorithm_name: Optional[str] = None
    custom_configuration: Optional[AlgorithmConfiguration] = None
    tag: Optional[str] = None
