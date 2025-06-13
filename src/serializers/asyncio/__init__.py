"""Async wrappers for the solid streaming parsers."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Callable


class AsyncWrapper:
    """Wrap a synchronous parser exposing async methods."""

    def __init__(self, parser_factory: Callable[[], Any]):
        self._parser = parser_factory()
        self._lock = asyncio.Lock()

    async def consume_async(self, buffer: Any) -> None:
        """Asynchronously consume data using a background thread."""
        async with self._lock:
            await asyncio.to_thread(self._parser.consume, buffer)

    def consume(self, buffer: Any) -> None:
        """Consume data blocking the caller."""
        asyncio.run(self.consume_async(buffer))

    async def get_async(self) -> Dict[str, Any]:
        """Asynchronously retrieve parsed data."""
        async with self._lock:
            return await asyncio.to_thread(self._parser.get)

    def get(self) -> Dict[str, Any]:
        """Retrieve parsed data synchronously."""
        return self._parser.get()
