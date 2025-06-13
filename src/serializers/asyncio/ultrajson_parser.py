"""Asynchronous wrapper around the solid ultrajson_parser implementation."""

from __future__ import annotations

from typing import Any, Dict

from serializers.asyncio import AsyncWrapper
from serializers.solid import ultrajson_parser as solid


class StreamingJsonParser(AsyncWrapper):
    """Async version of :class:`solid.StreamingJsonParser`."""

    def __init__(self) -> None:
        super().__init__(solid.StreamingJsonParser)
