import json
import os
from logging import StreamHandler
from typing import final, Type, TypeVar, Optional, Dict

from adapta.logs._async_logger import _AsyncLogger, create_async_logger
from adapta.logs.handlers.datadog_api_handler import DataDogApiHandler
from adapta.logs.models import LogLevel

TLogger = TypeVar("TLogger")


@final
class LoggerFactory:
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
    ) -> _AsyncLogger[TLogger]:
        return create_async_logger(
            logger_type=logger_type,
            log_handlers=self._log_handlers,
            min_log_level=LogLevel(os.getenv("NEXUS__LOG_LEVEL", "INFO")),
            fixed_template=fixed_template,
            fixed_template_delimiter=fixed_template_delimiter,
        )
