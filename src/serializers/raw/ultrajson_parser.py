# src/serializers/raw/ultrajson_parser.py

"""
src/serializers/raw/ultrajson_parser.py

Streaming JSON parser inspired by UltraJSON’s performance optimizations.

This parser:
  - Buffers incoming JSON text chunks (complete or partial).
  - Uses local-variable binding and minimal attribute lookups
    in hot loops to emulate UltraJSON’s C-level speed.
  - Incrementally re-parses the buffer in get(), extracting:
      * Partial string values (returned as-is so far)
      * Fully or partially streamed nested objects
      * Numbers, booleans, and null (only once complete)
  - Never imports Python’s built-in json module.
"""

from typing import Any, Dict, Tuple


class StreamingJsonParser:
    def __init__(self):
        """Initialize with an empty input buffer."""
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
        Return the current parse state as a Python dict by re-parsing
        the buffered text.
        """
        obj, _, _ = self._parse_obj(self._buf, 0)
        return obj

    def _parse_obj(self, s: str, i: int) -> Tuple[Dict[str, Any], int, bool]:
        # local bindings for speed
        n = len(s)
        if i >= n or s[i] != "{":
            return {}, i, False
        i += 1
        result: Dict[str, Any] = {}
        is_space = str.isspace

        # skip whitespace
        while i < n and is_space(s[i]):
            i += 1

        while i < n:
            ch = s[i]
            if ch == "}":
                return result, i + 1, True
            if ch != '"':
                break

            # parse key
            key, i, closed = self._parse_str(s, i)
            if not closed:
                break

            # skip whitespace + colon
            while i < n and is_space(s[i]):
                i += 1
            if i >= n or s[i] != ":":
                break
            i += 1
            while i < n and is_space(s[i]):
                i += 1
            if i >= n:
                result[key] = None
                break

            # parse value
            val, i, done = self._parse_val(s, i)
            # inclusion rules
            if isinstance(val, str) or isinstance(val, dict) or done:
                result[key] = val

            # skip whitespace and optional comma
            while i < n and is_space(s[i]):
                i += 1
            if i < n and s[i] == ",":
                i += 1
                while i < n and is_space(s[i]):
                    i += 1
                continue
            # otherwise loop to look for closing brace
        return result, i, False

    def _parse_str(self, s: str, i: int) -> Tuple[str, int, bool]:
        # s[i] == '"'
        i += 1
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
        return "".join(buf), i, False

    def _parse_val(self, s: str, i: int) -> Tuple[Any, int, bool]:
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
        if s.startswith("true", i):
            return True, i + 4, True
        if s.startswith("false", i):
            return False, i + 5, True
        if s.startswith("null", i):
            return None, i + 4, True
        # number
        numchars = "+-0123456789.eE"
        j = i
        while j < n and s[j] in numchars:
            j += 1
        if j > i:
            tok = s[i:j]
            try:
                if any(x in tok for x in ".eE"):
                    return float(tok), j, True
                return int(tok), j, True
            except ValueError:
                return tok, j, True
        # nothing recognized
        return None, i, False
