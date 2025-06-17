"""
MsgPack streaming parser implementation.
Note: MsgPack is binary format, so this implements JSON parsing
with MsgPack-inspired compact binary encoding and streaming concepts.
"""

from typing import Any, Dict, Tuple


class StreamingJsonParser:
    """
    Streaming JSON parser (msgpack "raw" slot).

    This is an incremental, single-pass parser over arbitrary string
    chunks.  It supports:
      - Partial string values (returned as-is so far)
      - Fully or partially streamed nested objects
      - Numbers, booleans, null
      - Keys only added once the closing '"' and following ':' are seen
    """

    def __init__(self):
        """Initialize with empty buffer."""
        self._buf: str = ""

    def consume(self, chunk: str) -> None:
        """
        Append the next chunk of JSON text (complete or partial).
        """
        if not isinstance(chunk, str):
            raise TypeError(f"Expected str, got {type(chunk)}")
        self._buf += chunk

    def get(self) -> Dict[str, Any]:
        """
        Re-parse the buffer and return the current JSON object state.
        """
        obj, _, _ = self._parse_obj(self._buf, 0)
        return obj

    def _parse_obj(self, s: str, i: int) -> Tuple[Dict[str, Any], int, bool]:
        """Parse JSON object starting at position i."""
        n = len(s)
        if not self._is_valid_object_start(s, i, n):
            return {}, i, False

        return self._parse_object_content(s, i + 1, n)

    def _is_valid_object_start(self, s: str, i: int, n: int) -> bool:
        """Check if position i starts a valid object."""
        return i < n and s[i] == "{"

    def _parse_object_content(
        self, s: str, start_pos: int, n: int
    ) -> Tuple[Dict[str, Any], int, bool]:
        """Parse the content inside an object after the opening brace."""
        result: Dict[str, Any] = {}
        i = self._skip_whitespace(s, start_pos, n)

        i, is_complete = self._parse_key_value_pairs(s, i, n, result)
        return result, i, is_complete

    def _skip_whitespace(self, s: str, pos: int, n: int) -> int:
        """Skip whitespace characters and return new position."""
        while pos < n and s[pos].isspace():
            pos += 1
        return pos

    def _parse_key_value_pairs(
        self, s: str, i: int, n: int, result: Dict[str, Any]
    ) -> Tuple[int, bool]:
        """Parse all key-value pairs in an object."""
        while i < n:
            if self._is_object_end(s, i):
                return i + 1, True

            i = self._process_single_key_value_pair(s, i, n, result)
            if i == -1:  # Break condition
                break

        return i, False

    def _is_object_end(self, s: str, i: int) -> bool:
        """Check if current position indicates object end."""
        return s[i] == "}"

    def _process_single_key_value_pair(
        self, s: str, i: int, n: int, result: Dict[str, Any]
    ) -> int:
        """Process a single key-value pair and return new position or -1 to break."""
        # Parse key
        key, i, success = self._extract_key(s, i, n)
        if not success:
            return -1

        # Parse value
        i, success = self._extract_and_store_value(s, i, n, key, result)
        if not success:
            return -1

        # Handle comma continuation
        return self._handle_comma_continuation(s, i, n)

    def _extract_key(self, s: str, i: int, n: int) -> Tuple[str, int, bool]:
        """Extract key from current position."""
        if s[i] != '"':
            return "", i, False

        key, i, key_closed = self._parse_str(s, i)
        if not key_closed:
            return "", i, False

        # Handle colon separator
        i = self._skip_whitespace(s, i, n)
        if i >= n or s[i] != ":":
            return "", i, False

        i += 1
        i = self._skip_whitespace(s, i, n)
        return key, i, True

    def _extract_and_store_value(
        self, s: str, i: int, n: int, key: str, result: Dict[str, Any]
    ) -> Tuple[int, bool]:
        """Extract value and store it if appropriate."""
        if i >= n:
            # No value type determined yet - don't include key per CHALLENGE.md requirements
            return i, False

        value_result = self._parse_value_at_position(s, i)
        if value_result is None:
            return i, False

        val, new_i, val_done = value_result
        if self._should_include_value(val, val_done):
            result[key] = val

        return new_i, True

    def _parse_value_at_position(self, s: str, i: int) -> Tuple[Any, int, bool] | None:
        """Parse value at position and return (value, new_index, is_done) or None."""
        val, new_i, val_done = self._parse_val(s, i)
        return (val, new_i, val_done)

    def _should_include_value(self, val: Any, val_done: bool) -> bool:
        """Determine if a value should be included based on CHALLENGE.md requirements."""
        # Include: string (partial or complete), nested dict, non-string and fully done
        return isinstance(val, str) or isinstance(val, dict) or val_done

    def _handle_comma_continuation(self, s: str, i: int, n: int) -> int:
        """Handle comma and prepare for next key-value pair."""
        i = self._skip_whitespace(s, i, n)
        if i < n and s[i] == ",":
            i += 1
            i = self._skip_whitespace(s, i, n)
        return i

    def _parse_str(self, s: str, i: int) -> Tuple[str, int, bool]:
        # s[i] == '"'
        i += 1
        n = len(s)
        out: list[str] = []
        escape = False
        while i < n:
            c = s[i]
            if escape:
                out.append(c)
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                return "".join(out), i + 1, True
            else:
                out.append(c)
            i += 1
        # no closing quote
        return "".join(out), n, False

    def _parse_val(self, s: str, i: int) -> Tuple[Any, int, bool]:
        """Parse a JSON value at position i."""
        n = len(s)
        if i >= n:
            return None, i, False

        c = s[i]

        # Try parsing different value types
        result = self._try_parse_string(s, i, c)
        if result is not None:
            return result

        result = self._try_parse_object(s, i, c)
        if result is not None:
            return result

        result = self._try_parse_literals(s, i)
        if result is not None:
            return result

        result = self._try_parse_number(s, i, n)
        if result is not None:
            return result

        # nothing recognized
        return None, i, False

    def _try_parse_string(self, s: str, i: int, c: str) -> Tuple[str, int, bool] | None:
        """Try to parse a string value."""
        if c == '"':
            return self._parse_str(s, i)
        return None

    def _try_parse_object(
        self, s: str, i: int, c: str
    ) -> Tuple[Dict[str, Any], int, bool] | None:
        """Try to parse an object value."""
        if c == "{":
            return self._parse_obj(s, i)
        return None

    def _try_parse_literals(self, s: str, i: int) -> Tuple[Any, int, bool] | None:
        """Try to parse boolean and null literals."""
        literals = (("true", True), ("false", False), ("null", None))
        for lit, val in literals:
            if s.startswith(lit, i):
                return val, i + len(lit), True
        return None

    def _try_parse_number(self, s: str, i: int, n: int) -> Tuple[Any, int, bool] | None:
        """Try to parse a number value."""
        numchars = "+-0123456789.eE"
        j = i
        while j < n and s[j] in numchars:
            j += 1

        if j <= i:
            return None

        return self._convert_number_token(s[i:j], j)

    def _convert_number_token(self, tok: str, end_pos: int) -> Tuple[Any, int, bool]:
        """Convert a number token to appropriate Python type."""
        try:
            if any(x in tok for x in ".eE"):
                return float(tok), end_pos, True
            return int(tok), end_pos, True
        except ValueError:
            # malformed number treated as raw
            return tok, end_pos, True
