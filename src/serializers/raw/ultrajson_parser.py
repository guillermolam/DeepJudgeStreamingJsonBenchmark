# src/serializers/raw/ultrajson_parser.py

"""
src/serializers/raw/ultrajson_parser.py

Streaming JSON parser inspired by UltraJSON’s performance optimizations.
This refactored parser:
  - Accepts byte-based input for JSON text chunks.
  - Uses a state machine to incrementally parse the JSON content.
  - Decodes UTF-8 explicitly when complete string tokens are formed.
  - Supports returning partially completed string values.
  - Excludes incomplete keys from the result.
  - Aims for efficiency and robustness, failing gracefully on malformed input.
"""

from typing import Any, Dict, Optional

# State constants for the parser
_ST_EXPECT_OBJ_START = 0
_ST_EXPECT_KEY_START = 1  # After '{' or ','
_ST_IN_KEY = 2
_ST_IN_KEY_ESCAPE = 3
_ST_EXPECT_COLON = 4
_ST_EXPECT_VALUE_START = 5
_ST_IN_STRING_VALUE = 6
_ST_IN_STRING_VALUE_ESCAPE = 7
_ST_IN_NUMBER = 8
_ST_IN_TRUE = 9
_ST_IN_FALSE = 10
_ST_IN_NULL = 11
_ST_EXPECT_COMMA_OR_OBJ_END = 12
_ST_OBJ_END = 13
_ST_ERROR = 99

_WHITESPACE = b" \t\n\r"
_DIGITS = b"0123456789"
_NUMBER_CHARS = _DIGITS + b"-.eE+"

class StreamingJsonParser:
    """
    A streaming JSON parser that processes byte-based input incrementally.
    It can handle partial JSON objects and incomplete string values,
    returning the currently parsed data structure at any point.
    """

    def __init__(self):
        """Initializes the streaming JSON parser."""
        self._buffer = bytearray()
        self._result: Dict[str, Any] = {}
        self._state = _ST_EXPECT_OBJ_START

        self._current_key_bytes = bytearray()
        self._current_value_bytes = bytearray()
        
        self._active_key: Optional[str] = None # Stores the decoded string of the last fully parsed key
        self._idx = 0 # Current parsing index within self._buffer

    def consume(self, buffer: str) -> None:
        """
        Consumes a chunk of JSON data.

        Args:
            buffer: A string containing a part of the JSON document.
        """
        if not isinstance(buffer, str):
            # As per spec, "Fail gracefully". For a type error on consume,
            # ignoring the chunk or transitioning to an error state is an option.
            # Here, we choose to ignore invalid chunk types.
            return
        # Convert string to bytes for internal processing
        chunk = buffer.encode('utf-8')
        self._buffer.extend(chunk)
        self._process_buffer()

    def get(self) -> Dict[str, Any]:
        """
        Returns the current state of the parsed JSON object.
        This includes any fully parsed key-value pairs and partially
        completed string values if a key has been fully parsed.
        Incomplete keys are not included.

        Returns:
            A dictionary representing the currently parsed JSON object.
        """
        output_dict = self._result.copy()

        if self._active_key is not None and self._state == _ST_IN_STRING_VALUE:
            if self._current_value_bytes:
                try:
                    # 'replace' ensures that even if a multi-byte UTF-8 char is split,
                    # we get what's decodable.
                    partial_value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                    output_dict[self._active_key] = partial_value_str
                except Exception:
                    # Fallback, though 'replace' should prevent most decode errors.
                    # This path should ideally not be hit.
                    pass 
        return output_dict

    def _handle_escape_char(self, byte_val: int) -> int:
        """
        Handles JSON escape sequences.
        Args:
            byte_val: The byte value of the character following a backslash.
        Returns:
            The byte value of the character to be appended to the string.
        """
        if byte_val == b'"'[0]: return b'"'[0]
        if byte_val == b'\\'[0]: return b'\\'[0]
        if byte_val == b'/'[0]: return b'/'[0]
        if byte_val == b'b'[0]: return b'\b'[0]
        if byte_val == b'f'[0]: return b'\f'[0]
        if byte_val == b'n'[0]: return b'\n'[0]
        if byte_val == b'r'[0]: return b'\r'[0]
        if byte_val == b't'[0]: return b'\t'[0]
        # Note: \uXXXX unicode escapes are not handled in this simplified version
        # for brevity and performance focus. JSON spec says other escapes are
        # the char itself.
        return byte_val

    def _finalize_value(self, value: Any):
        """Helper to assign a parsed value to the active key and reset."""
        if self._active_key is not None:
            self._result[self._active_key] = value
        self._active_key = None
        self._current_value_bytes.clear()
        self._state = _ST_EXPECT_COMMA_OR_OBJ_END
        
    def _parse_and_finalize_number(self):
        """Parses the number in _current_value_bytes and finalizes it."""
        if not self._current_value_bytes:
            self._state = _ST_ERROR; return False # Should not happen if started with a digit/minus

        num_str = self._current_value_bytes.decode('utf-8') # Numbers are ASCII

        # Basic validation to prevent float/int conversion errors on partials like "-"
        if num_str == "-" or num_str == "+" or num_str.endswith(('.', 'e', 'E', '+', '-')):
             # If it ends with these, it's potentially incomplete.
             # For "fail gracefully", we might treat it as an error or wait for more input.
             # Given the current byte is a delimiter, it implies the number *should* be complete.
             # So, this is likely a malformed number.
            self._state = _ST_ERROR; return False

        try:
            if any(c in num_str for c in ('.', 'e', 'E')):
                parsed_num = float(num_str)
            else:
                parsed_num = int(num_str)
            self._finalize_value(parsed_num)
            return True
        except ValueError: # Malformed number
            self._state = _ST_ERROR; return False

    def _process_buffer(self):
        """Processes the internal buffer to parse JSON content using a state machine."""
        buffer_len = len(self._buffer)
        while self._idx < buffer_len:
            byte = self._buffer[self._idx]

            if self._state == _ST_EXPECT_OBJ_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b'{'[0]: self._state = _ST_EXPECT_KEY_START; self._idx += 1
                else: self._state = _ST_ERROR; return # Invalid start
            
            elif self._state == _ST_EXPECT_KEY_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b'"'[0]:
                    self._state = _ST_IN_KEY
                    self._current_key_bytes.clear()
                    self._active_key = None 
                    self._idx += 1
                elif byte == b'}'[0]: self._state = _ST_OBJ_END; self._idx += 1
                else: self._state = _ST_ERROR; return # Expected key or '}'

            elif self._state == _ST_IN_KEY:
                if byte == b'\\'[0]: self._state = _ST_IN_KEY_ESCAPE; self._idx += 1
                elif byte == b'"'[0]:
                    try:
                        self._active_key = self._current_key_bytes.decode('utf-8')
                        self._state = _ST_EXPECT_COLON
                    except UnicodeDecodeError:
                        self._active_key = None; self._state = _ST_ERROR; return # Invalid UTF-8 in key
                    self._idx += 1
                else: self._current_key_bytes.append(byte); self._idx += 1
            
            elif self._state == _ST_IN_KEY_ESCAPE:
                self._current_key_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_KEY; self._idx += 1

            elif self._state == _ST_EXPECT_COLON:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b':'[0]: self._state = _ST_EXPECT_VALUE_START; self._idx += 1
                else: self._state = _ST_ERROR; return # Expected ':'

            elif self._state == _ST_EXPECT_VALUE_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                self._current_value_bytes.clear()
                if byte == b'"'[0]: self._state = _ST_IN_STRING_VALUE; self._idx += 1
                elif byte == b't'[0]: self._state = _ST_IN_TRUE; self._current_value_bytes.append(byte); self._idx += 1
                elif byte == b'f'[0]: self._state = _ST_IN_FALSE; self._current_value_bytes.append(byte); self._idx += 1
                elif byte == b'n'[0]: self._state = _ST_IN_NULL; self._current_value_bytes.append(byte); self._idx += 1
                elif byte in _NUMBER_CHARS and (byte != b'+'[0]): # '+' only valid after e/E or at start
                    self._state = _ST_IN_NUMBER; self._current_value_bytes.append(byte); self._idx += 1
                else: self._state = _ST_ERROR; return # Invalid value start

            elif self._state == _ST_IN_STRING_VALUE:
                if byte == b'\\'[0]: self._state = _ST_IN_STRING_VALUE_ESCAPE; self._idx += 1
                elif byte == b'"'[0]:
                    if self._active_key is not None:
                        try:
                            value_str = self._current_value_bytes.decode('utf-8')
                            self._finalize_value(value_str)
                        except UnicodeDecodeError: # Should be rare with good escape handling
                            value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                            self._finalize_value(value_str)
                    else: # No active key, error or unexpected structure
                        self._state = _ST_ERROR; return
                    self._idx += 1
                else: self._current_value_bytes.append(byte); self._idx += 1

            elif self._state == _ST_IN_STRING_VALUE_ESCAPE:
                self._current_value_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_STRING_VALUE; self._idx += 1
            
            elif self._state == _ST_IN_TRUE:
                self._current_value_bytes.append(byte); self._idx += 1
                if self._current_value_bytes == b"true": self._finalize_value(True)
                elif not b"true".startswith(self._current_value_bytes): self._state = _ST_ERROR; return
            
            elif self._state == _ST_IN_FALSE:
                self._current_value_bytes.append(byte); self._idx += 1
                if self._current_value_bytes == b"false": self._finalize_value(False)
                elif not b"false".startswith(self._current_value_bytes): self._state = _ST_ERROR; return

            elif self._state == _ST_IN_NULL:
                self._current_value_bytes.append(byte); self._idx += 1
                if self._current_value_bytes == b"null": self._finalize_value(None)
                elif not b"null".startswith(self._current_value_bytes): self._state = _ST_ERROR; return
            
            elif self._state == _ST_IN_NUMBER:
                if byte in _NUMBER_CHARS: # Simplified check, full validation is complex
                    self._current_value_bytes.append(byte); self._idx += 1
                else: # Delimiter found, number should be complete
                    if not self._parse_and_finalize_number(): return # Error in number parsing
                    # Delimiter byte (current `byte`) is not consumed by number, process in next state
            
            elif self._state == _ST_EXPECT_COMMA_OR_OBJ_END:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b','[0]: self._state = _ST_EXPECT_KEY_START; self._idx += 1
                elif byte == b'}'[0]: self._state = _ST_OBJ_END; self._idx += 1
                else: self._state = _ST_ERROR; return # Expected ',' or '}'

            elif self._state == _ST_OBJ_END:
                if byte in _WHITESPACE: self._idx += 1; continue # Allow trailing whitespace
                self._state = _ST_ERROR; return # Unexpected char after object end

            elif self._state == _ST_ERROR:
                return # In error state, consume no more from this chunk

            else: # Should not happen
                self._state = _ST_ERROR; return
        
        # Trim processed part of the buffer
        if self._idx > 0:
            self._buffer = self._buffer[self._idx:]
            self._idx = 0

# Mandatory tests
def test_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}')
    assert parser.get() == {"foo": "bar"}

def test_chunked_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": ')
    parser.consume('"bar"}')
    assert parser.get() == {"foo": "bar"}

def test_partial_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar')
    assert parser.get() == {"foo": "bar"}

# Example of running tests if the module is executed directly
if __name__ == '__main__':
    # Test 1: Complete JSON object
    parser1 = StreamingJsonParser()
    parser1.consume('{"key1": "value1", "key2": 123, "key3": true, "key4": null}')
    print(f"Test 1 Result: {parser1.get()}")
    assert parser1.get() == {"key1": "value1", "key2": 123, "key3": True, "key4": None}

    # Test 2: Chunked input
    parser2 = StreamingJsonParser()
    parser2.consume('{"name": "js')
    print(f"Test 2 Partial 1: {parser2.get()}") # Should be {"name": "js"}
    assert parser2.get() == {"name": "js"}
    parser2.consume('on", "age": 30, ')
    print(f"Test 2 Partial 2: {parser2.get()}") # Should be {"name": "json", "age": 30}
    assert parser2.get() == {"name": "json", "age": 30}
    parser2.consume('"city": "New York"}')
    print(f"Test 2 Final: {parser2.get()}")
    assert parser2.get() == {"name": "json", "age": 30, "city": "New York"}

    # Test 3: Partial string value at the end
    parser3 = StreamingJsonParser()
    parser3.consume('{"description": "A partial string')
    print(f"Test 3 Result: {parser3.get()}")
    assert parser3.get() == {"description": "A partial string"}

    # Test 4: Incomplete key
    parser4 = StreamingJsonParser()
    parser4.consume('{"incomplete_ke')
    print(f"Test 4 Result: {parser4.get()}") # Should be {}
    assert parser4.get() == {}
    parser4.consume('y": "value"}')
    print(f"Test 4 Final: {parser4.get()}")
    assert parser4.get() == {"incomplete_key": "value"}
    
    # Test 5: Number parsing
    parser5 = StreamingJsonParser()
    parser5.consume('{"num": -1.23e+2}')
    print(f"Test 5 Result: {parser5.get()}")
    assert parser5.get() == {"num": -123.0}

    # Test 6: All mandatory tests
    test_streaming_json_parser()
    test_chunked_streaming_json_parser()
    test_partial_streaming_json_parser()

    print("All tests passed successfully!")
