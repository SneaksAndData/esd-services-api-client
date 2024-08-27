import re
from abc import ABC, abstractmethod
from functools import partial

from adapta.logs import LoggerInterface
from adapta.metrics import MetricsProvider
from adapta.utils.decorators import run_time_metrics_async
from dataclasses_json.stringcase import snakecase


class UserTelemetryRecorder(ABC):
    def __init__(
        self,
        run_id: str,
        metrics_provider: MetricsProvider,
        logger: LoggerInterface,
        **kwargs
    ):
        self._run_id = run_id
        self._metrics_provider = metrics_provider
        self._logger = logger
        self._recorder_args = kwargs

    @property
    def _metric_tags(self) -> dict[str, str]:
        return {"recorder": self.__class__.alias().upper()}

    @abstractmethod
    async def _record(self, **user_telemetry):
        """
        Recording logic for this user recorder
        """

    async def record(self):
        @run_time_metrics_async(
            metric_name="user_telemetry_recording",
            on_finish_message_template="Finished recording telemetry from {recorder} in {elapsed:.2f}s seconds",
            template_args={
                "recorder": self.__class__.alias().upper(),
            },
        )
        async def _measured_recording(**run_args):
            return await self._record(**run_args)

        return await partial(
            _measured_recording,
            **self._recorder_args,
            metric_tags=self._metric_tags,
            metrics_provider=self._metrics_provider,
            logger=self._logger,
        )()

    @classmethod
    def alias(cls) -> str:
        """
        Alias to identify this recorder in logging and metrics data.
        """
        return snakecase(
            re.sub(
                r"(?<!^)(?=[A-Z])",
                "_",
                cls.__name__.lower(),
            )
        )
