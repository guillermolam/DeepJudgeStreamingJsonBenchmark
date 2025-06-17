"""
Streaming JSON parser that complies with the DeepJudge.ai requirements.
It processes JSON data incrementally and returns the current state.
"""

from typing import Dict, Any


class StreamingJsonParser:
    """
    Streaming JSON parser to handle partial and complete JSON objects.

    Constraints:
    - Only emits key-value pairs where keys are complete and values are either complete or valid partial strings.
    - Partial keys are never included in the result.
    """

    def __init__(self):
        self.buffer = ""
        self.stack = []
        self.current_key = None
        self.in_string = False
        self.escaped = False
        self.key_complete = False
        self.partial_value = ""
        self.result = {}
        self.state = "WAITING_KEY_OR_END"

    def consume(self, buffer: str) -> None:
        self.buffer += buffer
        i = 0
        while i < len(self.buffer):
            c = self.buffer[i]

            if self.state == "WAITING_KEY_OR_END":
                if c == '"':
                    self.in_string = True
                    self.current_key = ""
                    self.state = "READING_KEY"
                elif c == "}":
                    pass  # end of object
                # else: skip
            elif self.state == "READING_KEY":
                if self.escaped:
                    self.current_key += c
                    self.escaped = False
                elif c == "\\":
                    self.escaped = True
                elif c == '"':
                    self.in_string = False
                    self.key_complete = True
                    self.state = "WAITING_COLON"
                else:
                    self.current_key += c
            elif self.state == "WAITING_COLON":
                if c == ":":
                    self.state = "WAITING_VALUE"
            elif self.state == "WAITING_VALUE":
                if c == '"':
                    self.in_string = True
                    self.partial_value = ""
                    self.state = "READING_STRING_VALUE"
                elif c == "{":
                    self.stack.append({})
                    self.state = "READING_OBJECT"
                # else: skip or unsupported
            elif self.state == "READING_STRING_VALUE":
                if self.escaped:
                    self.partial_value += c
                    self.escaped = False
                elif c == "\\":
                    self.escaped = True
                elif c == '"':
                    self.result[self.current_key] = self.partial_value
                    self.reset_key_value_state()
                else:
                    self.partial_value += c
                    # Even if not closed, we may expose it in get()
            elif self.state == "READING_OBJECT":
                # We simplify by not supporting nested objects in this version
                self.reset_key_value_state()
            i += 1

        self.buffer = self.buffer[i:]

    def reset_key_value_state(self):
        self.current_key = None
        self.key_complete = False
        self.partial_value = ""
        self.state = "WAITING_KEY_OR_END"

    def get(self) -> Dict[str, Any]:
        if (
            self.current_key
            and self.partial_value
            and self.state == "READING_STRING_VALUE"
        ):
            # Include in-progress string value
            return {**self.result, self.current_key: self.partial_value}
        return self.result.copy()


if __name__ == "__main__":
    import pytest

    class TestStreamingJsonParser:
        def setup_method(self):
            self.parser = StreamingJsonParser()

        def test_init_empty(self):
            assert self.parser.get() == {}

        def test_complete_json(self):
            self.parser.consume('{"foo": "bar"}')
            assert self.parser.get() == {"foo": "bar"}

        def test_chunked_streaming(self):
            self.parser.consume('{"foo": ')
            self.parser.consume('"bar"}')
            assert self.parser.get() == {"foo": "bar"}

        def test_partial_string_value(self):
            self.parser.consume('{"hello": "worl')
            assert self.parser.get() == {"hello": "worl"}

        def test_partial_key_not_returned(self):
            self.parser.consume('{"par')
            assert self.parser.get() == {}

        def test_multiple_pairs_partial(self):
            self.parser.consume('{"a": "1", "b": 2')
            result = self.parser.get()
            assert result.get("a") == "1"
            if "b" in result:
                assert result["b"] == 2

        def test_boolean_and_null(self):
            self.parser.consume('{"t": true, "f": false, "n": null')
            result = self.parser.get()
            assert result.get("t") is True
            assert result.get("f") is False
            assert result.get("n") is None

        def test_nested_object_complete(self):
            self.parser.consume('{"outer": {"inner": "value"}}')
            assert self.parser.get() == {"outer": {"inner": "value"}}

        def test_nested_object_partial(self):
            self.parser.consume('{"outer": {"inner": "val')
            result = self.parser.get()
            assert "outer" in result and isinstance(result["outer"], dict)
            assert result["outer"].get("inner") == "val"

    pytest.main([__file__])
