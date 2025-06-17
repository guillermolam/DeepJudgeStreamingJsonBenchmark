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
        if idx >= n or s[idx] != "{":
            return {}, idx, False

        data: Dict[str, Any] = {}
        pos = idx + 1

        # skip whitespace
        while pos < n and s[pos].isspace():
            pos += 1

        while pos < n:
            # skip whitespace
            while pos < n and s[pos].isspace():
                pos += 1
            if pos >= n:
                break

            # closing brace
            if s[pos] == "}":
                return data, pos + 1, True

            # must start a key
            if s[pos] != '"':
                break
            key, pos, key_complete = self._parse_string(s, pos)
            if not key_complete:
                break

            # skip whitespace + colon
            while pos < n and s[pos].isspace():
                pos += 1
            if pos >= n or s[pos] != ":":
                break
            pos += 1
            while pos < n and s[pos].isspace():
                pos += 1
            if pos >= n:
                # no value yet
                data[key] = None
                break

            # parse value
            val, pos, val_complete = self._parse_value(s, pos)

            # include:
            #  - partial or complete strings,
            #  - nested dicts always,
            #  - any fully recognized non-string (number/boolean/null)
            if isinstance(val, str):
                data[key] = val
            elif isinstance(val, dict):
                data[key] = val
            elif val_complete:
                data[key] = val

            # skip whitespace + optional comma
            while pos < n and s[pos].isspace():
                pos += 1
            if pos < n and s[pos] == ",":
                pos += 1
                continue

        return data, pos, False

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
        # string
        if c == '"':
            return self._parse_string(s, idx)

        # nested object
        if c == "{":
            return self._parse_object(s, idx)

        # literals true/false/null
        for lit, val in (("true", True), ("false", False), ("null", None)):
            if s.startswith(lit, idx):
                return val, idx + len(lit), True

        # number (int or float)
        numchars = "+-0123456789.eE"
        i = idx
        while i < n and s[i] in numchars:
            i += 1
        if i > idx:
            tok = s[idx:i]
            try:
                if any(x in tok for x in ".eE"):
                    return float(tok), i, True
                else:
                    return int(tok), i, True
            except ValueError:
                # malformed number → return raw string
                return tok, i, True

        return None, idx, False


def check_solution(tests=None):
    from .. import run_module_tests
    import sys
    return run_module_tests(sys.modules[__name__], tests)
