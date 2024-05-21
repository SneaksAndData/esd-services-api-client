"""Serialization format module."""
from typing import final, Any

import pandas
from adapta.storage.models.format import (
    DataFrameParquetSerializationFormat,
    DictJsonSerializationFormat,
    SerializationFormat,
)


class Serializer:
    """
    Serialization format containing multiple formats. The format to use is determined at runtime by the type of the data.
    """

    def __init__(self, default_serialization_formats: dict = None):
        self._serialization_formats = (
            {}
            if default_serialization_formats is None
            else default_serialization_formats
        )

    def get_serialization_format(self, data: Any) -> type[SerializationFormat]:
        """
        Get the serializer for the data.
        """
        return self._serialization_formats[type(data)]

    def with_format(self, serialization_format: SerializationFormat) -> "Serializer":
        """Add a serialization format to the supported formats. Note that only 1 serialization format is allowed per
        type."""
        serialization_target_type = serialization_format.__orig_bases__[0].__args__[0]
        self._serialization_formats[serialization_target_type] = serialization_format

        return self

    def serialize(self, data) -> bytes:
        """
        Serialize data.
        """
        return self.get_serialization_format(data)().serialize(data)


@final
class TelemetrySerializer(Serializer):
    """Telemetry serialization format"""

    def __init__(self):
        super().__init__(
            default_serialization_formats={
                pandas.DataFrame: DataFrameParquetSerializationFormat,
                dict: DictJsonSerializationFormat,
            }
        )


@final
class ResultSerializer(Serializer):
    """Result serialization format"""

    def __init__(self):
        super().__init__(
            default_serialization_formats={
                pandas.DataFrame: DataFrameParquetSerializationFormat,
                dict: DictJsonSerializationFormat,
            }
        )
