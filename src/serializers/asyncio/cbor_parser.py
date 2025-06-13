"""
src/serializers/raw/cbor_parser.py

Streaming CBOR parser implementation (blocking, pure‐Python).
Consumes arbitrary byte‐chunks, buffers them until a full CBOR item
is available, decodes it via the cbor2 library, and makes
all decoded Python objects available via get().
"""

import io
from typing import Any, List
import cbor2
from cbor2 import CBORDecodeError


class StreamingJsonParser:
    """
    Streaming CBOR parser: consume() takes bytes (or bytearray) and
    extracts as many full CBOR items as possible. get() returns
    the list of decoded objects so far.
    """

    def __init__(self):
        """
        Initialize internal buffer and list of decoded objects.
        """
        self._buffer = b""
        self._decoded: List[Any] = []

    def consume(self, buffer: bytes) -> None:
        """
        Consume the next chunk of CBOR data.

        Args:
            buffer: bytes or bytearray containing 0 or more complete
                    (or partial) CBOR items back-to-back.
        Raises:
            TypeError: if buffer is not bytes or bytearray.
        """
        if not isinstance(buffer, (bytes, bytearray)):
            raise TypeError(f"Expected bytes or bytearray, got {type(buffer)}")

        # Append incoming data
        self._buffer += buffer

        # Try to decode as many complete items as possible
        stream = io.BytesIO(self._buffer)
        while True:
            start_pos = stream.tell()
            try:
                obj = cbor2.load(stream)
            except (CBORDecodeError, EOFError):
                # Not enough bytes to decode another item
                break
            # Successfully decoded one item
            self._decoded.append(obj)

        # Keep only the leftover bytes that were not consumed
        leftover = self._buffer[start_pos:]
        self._buffer = leftover

    def get(self) -> List[Any]:
        """
        Return a copy of all CBOR-decoded objects so far.

        Returns:
            List of Python objects in the order they were decoded.
        """
        return self._decoded.copy()
