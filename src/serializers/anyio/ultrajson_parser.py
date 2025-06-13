"""Asynchronous wrapper around the solid ultrajson_parser using AnyIO."""

from __future__ import annotations

from typing import Any, Dict
from serializers.anyio import AnyioWrapper
from serializers.solid import ultrajson_parser as solid


class StreamingJsonParser(AnyioWrapper):
    """AnyIO version of :class:`solid.StreamingJsonParser`."""

    def __init__(self) -> None:
        super().__init__(solid.StreamingJsonParser)
