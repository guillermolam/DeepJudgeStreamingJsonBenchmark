"""Asynchronous wrapper around the solid parquet_parser using AnyIO."""

from __future__ import annotations

from typing import Any, Dict
from serializers.anyio import AnyioWrapper
from serializers.solid import parquet_parser as solid


class StreamingJsonParser(AnyioWrapper):
    """AnyIO version of :class:`solid.StreamingJsonParser`."""

    def __init__(self) -> None:
        super().__init__(solid.StreamingJsonParser)

    def get_columnar_data(self) -> Dict[str, Any]:
        return self._parser.get_columnar_data()

    def get_metadata(self) -> Dict[str, Any]:
        return self._parser.get_metadata()
