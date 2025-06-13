"""Asynchronous wrapper around the solid parquet_parser implementation."""

from __future__ import annotations

from typing import Any, Dict

from serializers.asyncio import AsyncWrapper
from serializers.solid import parquet_parser as solid


class StreamingJsonParser(AsyncWrapper):
    """Async version of :class:`solid.StreamingJsonParser`."""

    def __init__(self) -> None:
        super().__init__(solid.StreamingJsonParser)

    def get_columnar_data(self) -> Dict[str, Any]:
        return self._parser.get_columnar_data()

    def get_metadata(self) -> Dict[str, Any]:
        return self._parser.get_metadata()
