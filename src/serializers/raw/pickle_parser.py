# src/serializers/raw/pickle_parser.py

"""
src/serializers/raw/pickle_parser.py

Streaming JSON parser inspired by Python’s pickle VM and its
stack-based opcode processing.

This parser:
  - Buffers arbitrary JSON text chunks (complete or partial).
  - Uses an explicit stack of (obj, current_key) frames to
    build nested dictionaries in a pickle-style manner.
  - Supports partial string values, full and partial nested objects,
    numbers, booleans, and null.
  - Only emits a key once its closing quote and colon are seen;
    partial string-values are returned as-is so far.
"""

from typing import Any, Dict, List, Tuple


class StreamingJsonParser:
    def __init__(self):
        """Initialize with an empty buffer and empty stack."""
        self._buf: str = ""

    def consume(self, chunk: str) -> None:
        """
        Consume the next chunk of JSON text.

        Args:
            chunk: A str containing 0 or more JSON characters
                   (complete or partial).
        """
        if not isinstance(chunk, str):
            raise TypeError(f"Expected str, got {type(chunk)}")
        self._buf += chunk

    def get(self) -> Dict[str, Any]:
        """
        Return the current parse state as a Python dict.

        Uses a stack-based rebuild each time, mirroring pickle’s
        PUSH/POP of frames for nested objects.
        """
        parsed, _, _ = self._parse_object(self._buf, 0)
        return parsed

    def _parse_object(
            self, s: str, idx: int
    ) -> Tuple[Dict[str, Any], int, bool]:
        """
        Parse an object `{...}` starting at s[idx].

        Returns (obj, new_idx, is_complete).
        """
        n = len(s)
        if idx >= n or s[idx] != "{":
            return {}, idx, False

        stack: List[Tuple[Dict[str, Any], Any]] = []
        current: Dict[str, Any] = {}
        current_key = None
        i = idx + 1

        while i < n:
            c = s[i]
            # skip whitespace
            if c.isspace():
                i += 1
                continue

            # end of this object
            if c == "}":
                if stack:
                    parent, key = stack.pop()
                    parent[key] = current
                    current = parent
                i += 1
                return current, i, not stack
            # comma → next pair in same object
            if c == ",":
                i += 1
                continue
            # expecting a key or a value continuation
            if current_key is None:
                # parse key
                if c != '"':
                    break
                key, i, closed = self._parse_string(s, i)
                if not closed:
                    break
                # skip whitespace + colon
                while i < n and s[i].isspace():
                    i += 1
                if i >= n or s[i] != ":":
                    break
                i += 1
                current_key = key
                continue
            # parse value for current_key
            val, i, done = self._parse_value(s, i)
            # decide whether to include
            if isinstance(val, str):
                current[current_key] = val
            elif isinstance(val, dict):
                current[current_key] = val
            elif done:
                current[current_key] = val
            # reset key
            current_key = None

            # skip on to comma or closing brace
            continue

        # incomplete
        return current, i, False

    def _parse_string(
            self, s: str, idx: int
    ) -> Tuple[str, int, bool]:
        """
        Parse a JSON string at s[idx]=='"'.

        Returns (content, new_idx, is_closed).
        """
        out: List[str] = []
        i = idx + 1
        escape = False
        n = len(s)
        while i < n:
            ch = s[i]
            if escape:
                out.append(ch)
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                return "".join(out), i + 1, True
            else:
                out.append(ch)
            i += 1
        # no closing quote
        return "".join(out), i, False

    def _parse_value(
            self, s: str, idx: int
    ) -> Tuple[Any, int, bool]:
        """
        Parse a JSON value at s[idx]: string, object, number,
        boolean, or null.

        Returns (value, new_idx, is_complete).
        """
        n = len(s)
        if idx >= n:
            return None, idx, False

        c = s[idx]
        # string
        if c == '"':
            return self._parse_string(s, idx)
        # nested object
        if c == "{":
            return self._parse_object(s, idx)
        # literals
        for lit, val in (("true", True), ("false", False), ("null", None)):
            if s.startswith(lit, idx):
                return val, idx + len(lit), True
        # number
        numchars = "+-0123456789.eE"
        j = idx
        while j < n and s[j] in numchars:
            j += 1
        if j > idx:
            tok = s[idx:j]
            try:
                if any(x in tok for x in ".eE"):
                    return float(tok), j, True
                return int(tok), j, True
            except ValueError:
                return tok, j, True

        return None, idx, False
