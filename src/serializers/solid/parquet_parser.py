# src/serializers/raw/parquet_parser.py

"""
src/serializers/raw/parquet_parser.py

Streaming JSON parser using a columnar-storage model inspired by Apache Parquet.

This parser:
  - Buffers incoming JSON text chunks (complete or partial).
  - Incrementally parses the buffer into individual columns (one per top-level key).
  - Maintains metadata (per-column counts and observed types).
  - Reconstructs the current JSON object on get() by assembling columns.

The columnar approach lets you inspect or extend per-field analytics (counts, types)
independently of the full-object view.
"""

from typing import Any, Dict, Tuple


class StreamingJsonParser:
    def __init__(self):
        """
        Initialize an empty buffer, an empty column store, and empty metadata.
        """
        self._buffer: str = ""
        # Columnar store: key → latest value
        self._columns: Dict[str, Any] = {}
        # Metadata per column: key → {'count': int, 'type': str}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def consume(self, chunk: str) -> None:
        """
        Consume the next chunk of JSON text (complete or partial).

        Args:
            chunk: str containing JSON fragment(s).
        """
        if not isinstance(chunk, str):
            raise TypeError(f"Expected str, got {type(chunk)}")
        self._buffer += chunk

    def get(self) -> Dict[str, Any]:
        """
        Return the current JSON object state as a dict.

        This re-parses the entire buffer, then updates the columnar store
        and metadata for any keys seen, and finally returns the assembled object.
        """
        obj, _, _ = self._parse_obj(self._buffer, 0)

        self._update_columnar_metadata(obj)
        return self._assemble_object_from_columns(obj)

    def _update_columnar_metadata(self, obj: Dict[str, Any]) -> None:
        """Update columnar store and metadata for parsed object."""
        for key, val in obj.items():
            self._columns[key] = val
            self._update_column_metadata(key, val)

    def _update_column_metadata(self, key: str, val: Any) -> None:
        """Update metadata for a specific column."""
        metadata = self._metadata.setdefault(key, {"count": 0, "type": None})
        metadata["count"] += 1
        metadata["type"] = type(val).__name__

    def _assemble_object_from_columns(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble the object from columns ensuring consistent ordering."""
        return {k: self._columns[k] for k in obj.keys()}

    # ─── Internal Parsing Helpers ─────────────────────────────────────────────

    def _parse_obj(self, s: str, i: int) -> Tuple[Dict[str, Any], int, bool]:
        """
        Parse a JSON object starting at s[i] == '{'.

        Returns:
            (parsed_dict, new_index, is_complete)
        """
        if not self._is_valid_object_start(s, i):
            return {}, i, False

        i += 1  # Skip opening brace
        result: Dict[str, Any] = {}
        i = self._skip_whitespace(s, i, len(s))

        return self._parse_object_content(s, i, result)

    def _is_valid_object_start(self, s: str, i: int) -> bool:
        """Check if position i contains a valid object start."""
        return i < len(s) and s[i] == "{"

    def _parse_object_content(self, s: str, i: int, result: Dict[str, Any]) -> Tuple[Dict[str, Any], int, bool]:
        """Parse the content inside JSON object braces."""
        n = len(s)

        while i < n:
            if self._is_object_end(s, i):
                return result, i + 1, True

            if not self._is_valid_key_start(s, i):
                break

            i = self._process_key_value_pair(s, i, n, result)
            if i == -1:  # Error occurred
                break

        return result, i, False

    def _is_object_end(self, s: str, i: int) -> bool:
        """Check if current position marks object end."""
        return s[i] == "}"

    def _is_valid_key_start(self, s: str, i: int) -> bool:
        """Check if current position is a valid key start."""
        return s[i] == '"'

    def _process_key_value_pair(self, s: str, i: int, n: int, result: Dict[str, Any]) -> int:
        """Process a single key-value pair and return new index or -1 on error."""
        key, value, new_i, should_break = self._parse_key_value_pair(s, i, n)

        if should_break:
            return -1

        if key is not None:
            result[key] = value

        return self._handle_comma_and_whitespace(s, new_i, n)

    def _skip_whitespace(self, s: str, i: int, n: int) -> int:
        """Skip whitespace characters and return new index."""
        while i < n and s[i].isspace():
            i += 1
        return i

    def _parse_key_value_pair(self, s: str, i: int, n: int) -> Tuple[Any, Any, int, bool]:
        """Parse a key-value pair and return (key, value, new_index, should_break)."""
        # Parse key
        key, i, key_complete = self._parse_key(s, i)
        if not key_complete:
            return None, None, i, True

        # Parse colon separator
        i, colon_found = self._parse_colon_separator(s, i, n)
        if not colon_found:
            return None, None, i, True

        # Parse value
        return self._parse_value_for_key(s, i, n, key)

    def _parse_key(self, s: str, i: int) -> Tuple[str, int, bool]:
        """Parse a JSON key and return (key, new_index, is_complete)."""
        return self._parse_str(s, i)

    def _parse_colon_separator(self, s: str, i: int, n: int) -> Tuple[int, bool]:
        """Parse the colon separator and return (new_index, found)."""
        i = self._skip_whitespace(s, i, n)
        if i >= n or s[i] != ":":
            return i, False

        i += 1
        i = self._skip_whitespace(s, i, n)
        return i, True

    def _parse_value_for_key(self, s: str, i: int, n: int, key: str) -> Tuple[Any, Any, int, bool]:
        """Parse value for a given key."""
        if i >= n:
            return key, None, i, True

        val, i, done = self._parse_val(s, i)

        if self._should_include_value(val, done):
            return key, val, i, False
        return None, None, i, False

    def _should_include_value(self, val: Any, done: bool) -> bool:
        """Check if value should be included based on columnar rules."""
        return isinstance(val, str) or isinstance(val, dict) or done

    def _handle_comma_and_whitespace(self, s: str, i: int, n: int) -> int:
        """Handle comma and whitespace after a key-value pair."""
        i = self._skip_whitespace(s, i, n)
        if i < n and s[i] == ",":
            i += 1
            i = self._skip_whitespace(s, i, n)
        return i

    def _parse_str(self, s: str, i: int) -> Tuple[str, int, bool]:
        """
        Parse a JSON string starting at s[i] == '"'.

        Returns:
            (content, new_index, is_closed)
        """
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

        # incomplete string
        return "".join(out), n, False

    def _parse_val(self, s: str, i: int) -> Tuple[Any, int, bool]:
        """
        Parse a JSON value at s[i]: string, object, number, boolean, or null.

        Returns:
            (value, new_index, is_complete)
        """
        n = len(s)
        if i >= n:
            return None, i, False

        c = s[i]

        # Handle different value types
        if c == '"':
            return self._parse_str(s, i)
        if c == "{":
            return self._parse_obj(s, i)

        # Try literals first
        literal_result = self._try_parse_literals(s, i)
        if literal_result:
            return literal_result

        # Try number parsing
        number_result = self._try_parse_number(s, i, n)
        if number_result:
            return number_result

        # Nothing matched
        return None, i, False

    def _try_parse_literals(self, s: str, i: int) -> Tuple[Any, int, bool] | None:
        """Try to parse boolean and null literals."""
        literals = (("true", True), ("false", False), ("null", None))
        for lit, val in literals:
            if s.startswith(lit, i):
                return val, i + len(lit), True
        return None

    def _try_parse_number(self, s: str, i: int, n: int) -> Tuple[Any, int, bool] | None:
        """Try to parse a number value."""
        num_chars = "+-0123456789.eE"
        j = i
        while j < n and s[j] in num_chars:
            j += 1

        if j <= i:
            return None

        return self._convert_number_token(s[i:j], j)

    def _convert_number_token(self, tok: str, end_pos: int) -> Tuple[Any, int, bool]:
        """Convert a number token to appropriate type."""
        try:
            if any(x in tok for x in ".eE"):
                return float(tok), end_pos, True
            return int(tok), end_pos, True
        except ValueError:
            return tok, end_pos, True
