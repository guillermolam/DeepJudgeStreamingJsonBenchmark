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

        # Update columnar store & metadata
        for key, val in obj.items():
            self._columns[key] = val
            m = self._metadata.setdefault(key, {"count": 0, "type": None})
            m["count"] += 1
            m["type"] = type(val).__name__

        # Assemble the object from columns (ensures consistent ordering)
        return {k: self._columns[k] for k in obj.keys()}

    # ─── Internal Parsing Helpers ─────────────────────────────────────────────

    def _parse_obj(self, s: str, i: int) -> Tuple[Dict[str, Any], int, bool]:
        """
        Parse a JSON object starting at s[i] == '{'.

        Returns:
            (parsed_dict, new_index, is_complete)
        """
        n = len(s)
        if i >= n or s[i] != "{":
            return {}, i, False
        i += 1
        result: Dict[str, Any] = {}

        # skip whitespace
        while i < n and s[i].isspace():
            i += 1

        while i < n:
            if s[i] == "}":
                return result, i + 1, True

            if s[i] != '"':
                break  # malformed or incomplete

            # key
            key, i, closed = self._parse_str(s, i)
            if not closed:
                break

            # skip to colon
            while i < n and s[i].isspace():
                i += 1
            if i >= n or s[i] != ":":
                break
            i += 1
            while i < n and s[i].isspace():
                i += 1
            if i >= n:
                result[key] = None
                break

            # value
            val, i, done = self._parse_val(s, i)
            # columnar inclusion rules:
            if isinstance(val, str) or isinstance(val, dict) or done:
                result[key] = val

            # skip whitespace and optional comma
            while i < n and s[i].isspace():
                i += 1
            if i < n and s[i] == ",":
                i += 1
                while i < n and s[i].isspace():
                    i += 1
                continue

        return result, i, False

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

        # string
        if c == '"':
            return self._parse_str(s, i)

        # object
        if c == "{":
            return self._parse_obj(s, i)

        # literals
        for lit, val in (("true", True), ("false", False), ("null", None)):
            if s.startswith(lit, i):
                return val, i + len(lit), True

        # number
        num_chars = "+-0123456789.eE"
        j = i
        while j < n and s[j] in num_chars:
            j += 1
        if j > i:
            tok = s[i:j]
            try:
                if any(x in tok for x in ".eE"):
                    return float(tok), j, True
                return int(tok), j, True
            except ValueError:
                return tok, j, True

        # nothing matched
        return None, i, False
