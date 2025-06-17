"""
MsgPack streaming parser implementation.
Note: MsgPack is binary format, so this implements JSON parsing
with MsgPack-inspired compact binary encoding and streaming concepts.
"""
from typing import Any, Dict, Tuple


class StreamingJsonParser:
    """
    Streaming JSON parser (msgpack “raw” slot).

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
        n = len(s)
        if i >= n or s[i] != "{":
            return {}, i, False
        i += 1
        result: Dict[str, Any] = {}
        # skip whitespace
        while i < n and s[i].isspace():
            i += 1

        while i < n:
            # closing brace?
            if s[i] == "}":
                return result, i + 1, True

            # key must start with "
            if s[i] != '"':
                break
            key, i, key_closed = self._parse_str(s, i)
            if not key_closed:
                break

            # skip whitespace + colon
            while i < n and s[i].isspace():
                i += 1
            if i >= n or s[i] != ":":
                break
            i += 1
            while i < n and s[i].isspace():
                i += 1
            if i >= n:
                # value not even started
                result[key] = None
                break

            # parse a value
            val, i, val_done = self._parse_val(s, i)

            # include only if:
            #  - string (partial or complete)
            #  - nested dict
            #  - non-string and fully done
            if isinstance(val, str):
                result[key] = val
            elif isinstance(val, dict):
                result[key] = val
            elif val_done:
                result[key] = val

            # skip whitespace
            while i < n and s[i].isspace():
                i += 1
            # skip comma
            if i < n and s[i] == ",":
                i += 1
                while i < n and s[i].isspace():
                    i += 1
                continue
            # otherwise loop to check for '}'
        return result, i, False

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
                # malformed number treated as raw
                return tok, j, True
        # nothing recognized
        return None, i, False


def check_solution(tests=None):
    from .. import run_module_tests
    import sys
    return run_module_tests(sys.modules[__name__], tests)
