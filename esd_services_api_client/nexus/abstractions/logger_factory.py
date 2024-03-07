"""
 Logger factory for async loggers.
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
import os
from logging import StreamHandler
from typing import final, Type, TypeVar, Optional, Dict

from adapta.logs import LoggerInterface, create_async_logger
from adapta.logs.handlers.datadog_api_handler import DataDogApiHandler
from adapta.logs.models import LogLevel

TLogger = TypeVar("TLogger")  # pylint: disable=C0103:


@final
class LoggerFactory:
    """
    Async logger provisioner.
    """

    def __init__(self):
        self._log_handlers = [
            StreamHandler(),
        ]
        if "NEXUS__DATADOG_LOGGER_CONFIGURATION" in os.environ:
            self._log_handlers.append(
                DataDogApiHandler(
                    **json.loads(os.getenv("NEXUS__DATADOG_LOGGER_CONFIGURATION"))
                )
            )

    def create_logger(
        self,
        logger_type: Type[TLogger],
        fixed_template: Optional[Dict[str, Dict[str, str]]] = None,
        fixed_template_delimiter=", ",
    ) -> LoggerInterface:
        """
        Creates an async-safe logger for the provided class name.
        """
        return create_async_logger(
            logger_type=logger_type,
            log_handlers=self._log_handlers,
            min_log_level=LogLevel(os.getenv("NEXUS__LOG_LEVEL", "INFO")),
            fixed_template=fixed_template,
            fixed_template_delimiter=fixed_template_delimiter,
        )
