from dataclasses import dataclass

from adapta.storage.models.format import DictJsonSerializationFormat
from adapta.utils import session_with_retries

from dataclasses_json import DataClassJsonMixin
from typing import final, Optional, Type


@dataclass
class AlgorithmPayload(DataClassJsonMixin):
    """
    Base class for algorithm payload
    """


@final
class AlgorithmPayloadReader:
    async def __aenter__(self):
        if not self._http:
            self._http = session_with_retries()
        http_response = self._http.get(url=self._payload_uri)
        http_response.raise_for_status()
        self._payload = self._payload_type.from_dict(
            DictJsonSerializationFormat().deserialize(http_response.content)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._http.close()
        self._http = None

    def __init__(self, payload_uri: str, payload_type: Type[AlgorithmPayload]):
        self._http = session_with_retries()
        self._payload: Optional[AlgorithmPayload] = None
        self._payload_uri = payload_uri
        self._payload_type = payload_type

    @property
    def payload_uri(self) -> Optional[str]:
        return self._payload_uri

    @property
    def payload(self) -> Optional[AlgorithmPayload]:
        return self._payload
