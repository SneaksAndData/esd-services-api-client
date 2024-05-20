"""Serialization format module."""
from _warnings import warn

import pandas
from adapta.storage.models.format import (
    DataFrameParquetSerializationFormat,
    DictJsonSerializationFormat,
    SerializationFormat,
)


class SerializationFormatContainer(SerializationFormat):
    """
    Magic serialization format.
    """

    def __init__(self, default_serialization_formats: dict = None):
        self._serialization_formats = (
            {}
            if default_serialization_formats is None
            else default_serialization_formats
        )

    def __call__(self):
        return self

    def get_serialization_format(self, data) -> SerializationFormat:
        """
        Get the serializer for the data.
        """
        return self._serialization_formats[type(data)]()

    def add_serialization_format(
        self, serialization_format: SerializationFormat
    ) -> None:
        """Add a serialization format to the supported formats. Note that only 1 serialization format is allowed per
        type."""

        serialization_target_type = serialization_format.__orig_bases__[0].__args__[0]

        if serialization_target_type in self._serialization_formats.keys():
            warn(
                f"A serialization format for objects of type {serialization_target_type} already exists."
                f"Replacing the current serializer {self._serialization_formats[serialization_target_type]} with {serialization_format.__class__.__name__}"
            )
        self._serialization_formats[
            serialization_target_type
        ] = serialization_format

    def serialize(self, data) -> bytes:
        """
        Serialize data.
        """
        serializer = self.get_serialization_format(data)
        return serializer.serialize(data)

    def deserialize(self, data: bytes):
        """
        Deserialize data.
        """
        raise NotImplementedError("Not supported")


class TelemetrySerializationFormat(SerializationFormatContainer):
    """Telemetry serialization format"""

    def __init__(self):
        super().__init__(
            default_serialization_formats={
                pandas.DataFrame: DataFrameParquetSerializationFormat,
                dict: DictJsonSerializationFormat,
            }
        )


class ResultSerializationFormat(SerializationFormatContainer):
    """Result serialization format"""

    def __init__(self):
        super().__init__(
            default_serialization_formats={
                pandas.DataFrame: DataFrameParquetSerializationFormat,
                dict: DictJsonSerializationFormat,
            }
        )
