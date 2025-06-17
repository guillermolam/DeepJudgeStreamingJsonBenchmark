# src/serializers/raw/protobuf_parser.py

"""
src/serializers/raw/protobuf_parser.py

Streaming JSON parser inspired by Protocol Buffers’ tag–wire–type model.

This parser:
  - Buffers arbitrary JSON text chunks (complete or partial).
  - Treats JSON object fields as “tags” and inspects the first character
    of each value to infer a wire type before dispatching to the appropriate
    value parser.
  - Supports partial string values, nested objects, numbers, booleans, and null.
  - Only emits a key once its closing quote and a value type are seen;
    partial keys (or keys with only a colon) are not returned.
"""

from typing import Any, Dict, Tuple


class StreamingJsonParser:
    def __init__(self):
        """
        Initialize with an empty text buffer.
        """
        self._buf: str = ""
        # Dispatch table: leading char → handler
        self._wire_handlers = {
            '"': self._parse_string,
            '{': self._parse_object,
            't': lambda s, i: self._match_literal(s, i, "true", True),
            'f': lambda s, i: self._match_literal(s, i, "false", False),
            'n': lambda s, i: self._match_literal(s, i, "null", None),
        }
        # Characters valid in a JSON number
        self._numchars = "+-0123456789.eE"

    def consume(self, chunk: str) -> None:
        """
        Append the next chunk of JSON text (complete or partial).

        Args:
            chunk: A str containing JSON fragment(s).
        """
        if not isinstance(chunk, str):
            raise TypeError(f"Expected str, got {type(chunk)}")
        self._buf += chunk

    def get(self) -> Dict[str, Any]:
        """
        Return the current parse state as a Python dict.

        Re-parses the internal buffer each call, extracting all
        fully or partially parsed fields per the streaming rules.
        """
        obj, _, _ = self._parse_object(self._buf, 0)
        return obj

    def _parse_object(
            self, s: str, idx: int
    ) -> Tuple[Dict[str, Any], int, bool]:
        """
        Parse a JSON object starting at s[idx] == '{'.

        Returns:
            (parsed_dict, new_index, is_complete)
        """
        n = len(s)
        if idx >= n or s[idx] != "{":
            return {}, idx, False
        idx += 1
        result: Dict[str, Any] = {}

        # skip whitespace
        while idx < n and s[idx].isspace():
            idx += 1

        while idx < n:
            # closing brace → end of object
            if s[idx] == "}":
                return result, idx + 1, True

            # must start a string key
            if s[idx] != '"':
                break
            key, idx, key_closed = self._parse_string(s, idx)
            if not key_closed:
                break

            # skip whitespace + colon
            while idx < n and s[idx].isspace():
                idx += 1
            if idx >= n or s[idx] != ":":
                break
            idx += 1

            # skip whitespace before value
            while idx < n and s[idx].isspace():
                idx += 1
            if idx >= n:
                # no value type detected yet → partial key only
                break

            # dispatch based on wire type (first char of value)
            val, idx, val_done = self._parse_value(s, idx)

            # include the field if:
            #  - string (partial or complete)
            #  - nested dict (partial or complete)
            #  - non-string and val_done==True
            if isinstance(val, str) or isinstance(val, dict) or val_done:
                result[key] = val

            # skip whitespace and optional comma
            while idx < n and s[idx].isspace():
                idx += 1
            if idx < n and s[idx] == ",":
                idx += 1
                # loop around for next key
                continue

            # otherwise, loop to check for closing '}' or end
        return result, idx, False

    def _parse_string(self, s: str, idx: int) -> Tuple[str, int, bool]:
        """
        Parse a JSON string at s[idx] == '"'.

        Returns:
            (content_without_quotes, new_index, is_closed)
        """
        idx += 1
        buf: list[str] = []
        escape = False
        n = len(s)
        while idx < n:
            ch = s[idx]
            if escape:
                buf.append(ch)
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                return "".join(buf), idx + 1, True
            else:
                buf.append(ch)
            idx += 1
        # no closing quote → partial string
        return "".join(buf), idx, False

    def _match_literal(
            self, s: str, idx: int, lit: str, val: Any
    ) -> Tuple[Any, int, bool]:
        """
        Attempt to match a literal (true/false/null) at s[idx:].

        Returns (value, new_index, is_complete).
        """
        end = idx + len(lit)
        # full literal present?
        if len(s) >= end:
            if s[idx:end] == lit:
                return val, end, True
            # mismatched literal → not a valid field here
            return None, idx, False
        # incomplete literal → wait for more
        return None, idx, False

    def _parse_number(self, s: str, idx: int) -> Tuple[Any, int, bool]:
        """
        Parse a JSON number (int or float) starting at s[idx].

        Returns (number, new_index, True) if at least one digit is consumed.
        """
        n = len(s)
        j = idx
        while j < n and s[j] in self._numchars:
            j += 1
        if j == idx:
            return None, idx, False
        tok = s[idx:j]
        try:
            if any(c in tok for c in ".eE"):
                return float(tok), j, True
            return int(tok), j, True
        except ValueError:
            # malformed number → treat as raw token
            return tok, j, True

    def _parse_value(self, s: str, idx: int) -> Tuple[Any, int, bool]:
        """
        Dispatch to the appropriate value parser based on the first char.
        """
        n = len(s)
        if idx >= n:
            return None, idx, False
        c = s[idx]
        # tag→wire dispatch
        if c in self._wire_handlers:
            return self._wire_handlers[c](s, idx)
        # numeric
        if c in self._numchars:
            return self._parse_number(s, idx)
        # unrecognized
        return None, idx, False


def check_solution(tests=None):
    from .. import run_module_tests
    import sys
    return run_module_tests(sys.modules[__name__], tests)
