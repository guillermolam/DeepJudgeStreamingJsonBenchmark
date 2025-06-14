"""AnyIO-based async wrappers for the solid streaming parsers."""

from __future__ import annotations

import anyio
from typing import Any, Callable, Dict


class AnyioWrapper:
    """Wrap a synchronous parser exposing async methods via AnyIO."""

    def __init__(self, parser_factory: Callable[[], Any]):
        self._parser = parser_factory()
        self._lock = anyio.Lock()

    async def consume_async(self, buffer: Any) -> None:
        """Asynchronously consume data using a background worker."""
        async with self._lock:
            await anyio.to_thread.run_sync(self._parser.consume, buffer)

    def consume(self, buffer: Any) -> None:
        """Consume data synchronously using AnyIO's runner."""
        anyio.run(self.consume_async, buffer)

    async def get_async(self) -> Dict[str, Any]:
        """Asynchronously retrieve parsed data."""
        async with self._lock:
            return await anyio.to_thread.run_sync(self._parser.get)

    def get(self) -> Dict[str, Any]:
        """Retrieve parsed data synchronously."""
        return self._parser.get()
