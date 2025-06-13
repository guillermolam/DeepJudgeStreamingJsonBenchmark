"""
src/serializers/raw/bson_parser.py

Streaming BSON parser implementation (blocking, pure‐Python).
Consumes arbitrary byte‐chunks, buffers them until a full BSON document
is available, decodes it via the PyMongo BSON library, and makes
all decoded documents available via get().
"""

from typing import Any, Dict, List
from bson import BSON, InvalidBSON


class StreamingJsonParser:
    """
    Streaming BSON parser: consume() takes bytes (or bytearray) and
    extracts as many full BSON documents as possible.  get() returns
    the list of dicts decoded so far.
    """

    def __init__(self):
        """
        Initialize internal buffer and decoded‐docs list.
        """
        self._buffer = b""
        self._docs: List[Dict[str, Any]] = []

    def consume(self, buffer: bytes) -> None:
        """
        Consume the next chunk of BSON data.

        Args:
            buffer: bytes or bytearray containing 0 or more complete
                    (or partial) BSON documents back-to-back.
        Raises:
            TypeError: if buffer is not bytes or bytearray.
            ValueError: if a length prefix is invalid.
            InvalidBSON: if decoding fails on a complete slice.
        """
        if not isinstance(buffer, (bytes, bytearray)):
            raise TypeError(f"Expected bytes or bytearray, got {type(buffer)}")

        # Append incoming data to our internal buffer
        self._buffer += buffer

        # Try to parse out as many full documents as we can
        while True:
            # Need at least 4 bytes to read the length prefix
            if len(self._buffer) < 4:
                break

            # BSON length is a little-endian int32 at the start
            length = int.from_bytes(self._buffer[:4], byteorder="little", signed=False)
            if length <= 0:
                raise ValueError(f"Invalid BSON document length: {length}")

            # Wait until we have the full document available
            if len(self._buffer) < length:
                break

            # Slice out one complete BSON document
            doc_bytes = self._buffer[:length]
            self._buffer = self._buffer[length:]

            # Decode it into a Python dict
            try:
                doc = BSON(doc_bytes).decode()
            except InvalidBSON as e:
                # Propagate decode errors on a supposedly-complete slice
                raise

            # Store for retrieval
            self._docs.append(doc)

    def get(self) -> List[Dict[str, Any]]:
        """
        Return a copy of all BSON documents decoded so far.

        Returns:
            List of dicts, in the order they were decoded.
        """
        return self._docs.copy()
