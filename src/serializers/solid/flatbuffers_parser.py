# src/serializers/raw/flatbuffers_parser.py

from typing import Any, Dict, Tuple


class StreamingJsonParser:
    """
    Streaming JSON parser (FlatBuffers “raw” slot).

    This implements a single-pass, incremental JSON object parser
    over arbitrary string chunks.  It supports:

      - Partial string values (you’ll get back whatever’s been read so far)
      - Complete and incomplete nested objects
      - Numbers, booleans, null
      - Discarding partially read keys until they finish
    """

    def __init__(self):
        """Initialize with an empty input buffer."""
        self.buffer: str = ""

    def consume(self, chunk: str) -> None:
        """
        Feed the next chunk of JSON text (complete or partial).

        Args:
            chunk: A string containing 0 or more JSON characters.
        """
        self.buffer += chunk

    def get(self) -> Dict[str, Any]:
        """
        Return the current parse state as a Python dict.

        This will include any keys whose values have at least begun parsing—
        full or partial string‐values, nested dicts, numbers, booleans, null.
        """
        obj, _, _ = self._parse_object(self.buffer, 0)
        return obj

    def _parse_object(self, s: str, idx: int) -> Tuple[Dict[str, Any], int, bool]:
        """
        Attempt to parse an object from s[idx:].

        Returns a tuple (obj, new_idx, is_complete), where:
          - obj is the dict of all fully or partially parsed pairs
          - new_idx is the index right after the closing '}' (or end of input)
          - is_complete is True if we saw the closing '}', else False
        """
        n = len(s)
        if not self._is_valid_object_start(s, idx, n):
            return {}, idx, False

        return self._parse_object_content(s, idx + 1, n)

    def _parse_object_content(
        self, s: str, start_pos: int, n: int
    ) -> Tuple[Dict[str, Any], int, bool]:
        """Parse the content inside an object after the opening brace."""
        data: Dict[str, Any] = {}
        pos = self._skip_whitespace(s, start_pos, n)

        pos, is_complete = self._parse_object_pairs(s, pos, n, data)
        return data, pos, is_complete

    def _parse_object_pairs(
        self, s: str, pos: int, n: int, data: Dict[str, Any]
    ) -> Tuple[int, bool]:
        """Parse key-value pairs inside an object."""
        while pos < n:
            pos = self._skip_whitespace(s, pos, n)
            if pos >= n:
                break

            if self._is_object_end(s, pos):
                return pos + 1, True

            pos = self._process_single_pair(s, pos, n, data)
            if pos == -1:  # Break condition
                break

        return pos, False

    def _process_single_pair(
        self, s: str, pos: int, n: int, data: Dict[str, Any]
    ) -> int:
        """Process a single key-value pair and return new position or -1 to break."""
        key, value_info, new_pos, should_break = self._parse_key_value_pair(s, pos, n)
        if should_break:
            return -1

        self._add_pair_to_data(data, key, value_info)
        return self._handle_comma_continuation(s, new_pos, n)

    def _add_pair_to_data(
        self, data: Dict[str, Any], key: str, value_info: Any
    ) -> None:
        """Add a key-value pair to the data dictionary if it should be included."""
        if not self._should_include_value(key, value_info):
            return

        if value_info is None:
            data[key] = None
        elif isinstance(value_info, tuple):
            val, _ = value_info
            data[key] = val
        else:
            data[key] = value_info

    def _is_valid_object_start(self, s: str, idx: int, n: int) -> bool:
        """Check if the position is a valid start of an object."""
        return idx < n and s[idx] == "{"

    def _skip_whitespace(self, s: str, pos: int, n: int) -> int:
        """Skip whitespace characters and return new position."""
        while pos < n and s[pos].isspace():
            pos += 1
        return pos

    def _is_object_end(self, s: str, pos: int) -> bool:
        """Check if current position indicates object end."""
        return s[pos] == "}"

    def _parse_key_value_pair(
        self, s: str, pos: int, n: int
    ) -> Tuple[str, Any, int, bool]:
        """Parse a key-value pair and return (key, value, new_pos, should_break)."""
        # Parse key
        key, pos, should_break = self._extract_key(s, pos)
        if should_break:
            return "", None, pos, True

        # Handle colon separator
        pos, should_break = self._process_colon_separator(s, pos, n)
        if should_break:
            return "", None, pos, True

        # Parse value
        return self._extract_value_for_key(s, pos, n, key)

    def _extract_key(self, s: str, pos: int) -> Tuple[str, int, bool]:
        """Extract key from current position."""
        if s[pos] != '"':
            return "", pos, True

        key, pos, key_complete = self._parse_string(s, pos)
        if not key_complete:
            return "", pos, True

        return key, pos, False

    def _process_colon_separator(self, s: str, pos: int, n: int) -> Tuple[int, bool]:
        """Process colon separator and return new position and break flag."""
        new_pos = self._handle_colon_separator(s, pos, n)
        if new_pos is None:
            return pos, True
        return new_pos, False

    def _extract_value_for_key(
        self, s: str, pos: int, n: int, key: str
    ) -> Tuple[str, Any, int, bool]:
        """Extract value for the given key."""
        if pos >= n:
            return key, None, pos, True

        val, pos, val_complete = self._parse_value(s, pos)
        return key, (val, val_complete), pos, False

    def _handle_colon_separator(self, s: str, pos: int, n: int) -> int | None:
        """Handle colon separator between key and value."""
        pos = self._skip_whitespace(s, pos, n)
        if pos >= n or s[pos] != ":":
            return None
        pos += 1
        return self._skip_whitespace(s, pos, n)

    def _should_include_value(self, key: str, value_info: Any) -> bool:
        """Determine if a key-value pair should be included in the result."""
        if not key:
            return False

        if value_info is None:
            return True  # Include key with None value

        if isinstance(value_info, tuple):
            val, val_complete = value_info
            # Include: partial or complete strings, nested dicts always,
            # any fully recognized non-string (number/boolean/null)
            return isinstance(val, str) or isinstance(val, dict) or val_complete

        return True

    def _handle_comma_continuation(self, s: str, pos: int, n: int) -> int:
        """Handle comma and continuation of parsing."""
        pos = self._skip_whitespace(s, pos, n)
        if pos < n and s[pos] == ",":
            pos += 1
        return pos

    def _parse_string(self, s: str, idx: int) -> Tuple[str, int, bool]:
        """
        Parse a JSON string beginning at s[idx]=='"'.

        Returns (content, new_idx, is_closed).
        If the closing quote is missing, content is whatever’s seen so far.
        """
        i = idx + 1
        buf: list[str] = []
        escape = False
        n = len(s)

        while i < n:
            c = s[i]
            if escape:
                buf.append(c)
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                return "".join(buf), i + 1, True
            else:
                buf.append(c)
            i += 1

        # no closing quote
        return "".join(buf), n, False

    def _parse_value(self, s: str, idx: int) -> Tuple[Any, int, bool]:
        """
        Parse a JSON value at s[idx]: string, object, number, boolean, or null.

        Returns (value, new_idx, is_complete).
        Partial strings return with is_complete=False.
        Nested objects bubble up their own completeness.
        """
        n = len(s)
        if idx >= n:
            return None, idx, False

        c = s[idx]

        # Handle different value types
        if c == '"':
            return self._parse_string(s, idx)
        if c == "{":
            return self._parse_object(s, idx)

        # Try parsing literals
        literal_result = self._try_parse_literals(s, idx)
        if literal_result is not None:
            return literal_result

        # Try parsing numbers
        number_result = self._try_parse_number(s, idx, n)
        if number_result is not None:
            return number_result

        return None, idx, False

    def _try_parse_literals(self, s: str, idx: int) -> Tuple[Any, int, bool] | None:
        """Try to parse boolean and null literals."""
        literals = (("true", True), ("false", False), ("null", None))
        for lit, val in literals:
            if s.startswith(lit, idx):
                return val, idx + len(lit), True
        return None

    def _try_parse_number(
        self, s: str, idx: int, n: int
    ) -> Tuple[Any, int, bool] | None:
        """Try to parse a number value."""
        numchars = "+-0123456789.eE"
        i = idx
        while i < n and s[i] in numchars:
            i += 1

        if i <= idx:
            return None

        return self._convert_number_token(s[idx:i], i)

    def _convert_number_token(self, tok: str, end_pos: int) -> Tuple[Any, int, bool]:
        """Convert a number token to appropriate type."""
        try:
            if any(x in tok for x in ".eE"):
                return float(tok), end_pos, True
            else:
                return int(tok), end_pos, True
        except ValueError:
            # malformed number → return raw string
            return tok, end_pos, True


def check_solution(tests=None):
    from .. import run_module_tests
    import sys
    return run_module_tests(sys.modules[__name__], tests)
