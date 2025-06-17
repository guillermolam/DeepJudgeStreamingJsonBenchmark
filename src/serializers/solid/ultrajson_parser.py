"""
Ultra-JSON streaming parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by Ultra-JSON high-performance techniques.
The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original Ultra-JSON-inspired helper classes remain but are no longer used by StreamingJsonParser.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

# --- Start of Refactored StreamingJsonParser and its dependencies ---
# (Identical to the implementation in raw/ultrajson_parser.py for consistency and compliance)

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
    This version replaces the original Ultra-JSON-style parser in this module.
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
            return # Ignore invalid chunk types gracefully
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
                    partial_value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                    output_dict[self._active_key] = partial_value_str
                except Exception:
                    pass 
        return output_dict

    def _handle_escape_char(self, byte_val: int) -> int:
        """Handles JSON escape sequences."""
        if byte_val == b'"'[0]: return b'"'[0]
        if byte_val == b'\\'[0]: return b'\\'[0]
        if byte_val == b'/'[0]: return b'/'[0]
        if byte_val == b'b'[0]: return b'\b'[0]
        if byte_val == b'f'[0]: return b'\f'[0]
        if byte_val == b'n'[0]: return b'\n'[0]
        if byte_val == b'r'[0]: return b'\r'[0]
        if byte_val == b't'[0]: return b'\t'[0]
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
            self._state = _ST_ERROR; return False

        num_str = self._current_value_bytes.decode('utf-8') 

        if num_str == "-" or num_str == "+" or num_str.endswith(('.', 'e', 'E', '+', '-')):
            self._state = _ST_ERROR; return False

        try:
            if any(c in num_str for c in ('.', 'e', 'E')):
                parsed_num = float(num_str)
            else:
                parsed_num = int(num_str)
            self._finalize_value(parsed_num)
            return True
        except ValueError: 
            self._state = _ST_ERROR; return False

    def _process_buffer(self):
        """Processes the internal buffer to parse JSON content using a state machine."""
        buffer_len = len(self._buffer)
        while self._idx < buffer_len:
            byte = self._buffer[self._idx]

            if self._state == _ST_EXPECT_OBJ_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b'{'[0]: self._state = _ST_EXPECT_KEY_START; self._idx += 1
                else: self._state = _ST_ERROR; return 
            
            elif self._state == _ST_EXPECT_KEY_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b'"'[0]:
                    self._state = _ST_IN_KEY
                    self._current_key_bytes.clear()
                    self._active_key = None 
                    self._idx += 1
                elif byte == b'}'[0]: self._state = _ST_OBJ_END; self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_IN_KEY:
                if byte == b'\\'[0]: self._state = _ST_IN_KEY_ESCAPE; self._idx += 1
                elif byte == b'"'[0]:
                    try:
                        self._active_key = self._current_key_bytes.decode('utf-8')
                        self._state = _ST_EXPECT_COLON
                    except UnicodeDecodeError:
                        self._active_key = None; self._state = _ST_ERROR; return 
                    self._idx += 1
                else: self._current_key_bytes.append(byte); self._idx += 1
            
            elif self._state == _ST_IN_KEY_ESCAPE:
                self._current_key_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_KEY; self._idx += 1

            elif self._state == _ST_EXPECT_COLON:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b':'[0]: self._state = _ST_EXPECT_VALUE_START; self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_EXPECT_VALUE_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                self._current_value_bytes.clear()
                if byte == b'"'[0]: self._state = _ST_IN_STRING_VALUE; self._idx += 1
                elif byte == b't'[0]: self._state = _ST_IN_TRUE; self._current_value_bytes.append(byte); self._idx += 1
                elif byte == b'f'[0]: self._state = _ST_IN_FALSE; self._current_value_bytes.append(byte); self._idx += 1
                elif byte == b'n'[0]: self._state = _ST_IN_NULL; self._current_value_bytes.append(byte); self._idx += 1
                elif byte in _NUMBER_CHARS and (byte != b'+'[0]): 
                    self._state = _ST_IN_NUMBER; self._current_value_bytes.append(byte); self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_IN_STRING_VALUE:
                if byte == b'\\'[0]: self._state = _ST_IN_STRING_VALUE_ESCAPE; self._idx += 1
                elif byte == b'"'[0]:
                    if self._active_key is not None:
                        try:
                            value_str = self._current_value_bytes.decode('utf-8')
                            self._finalize_value(value_str)
                        except UnicodeDecodeError: 
                            value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                            self._finalize_value(value_str)
                    else: 
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
                if byte in _NUMBER_CHARS: 
                    self._current_value_bytes.append(byte); self._idx += 1
                else: 
                    if not self._parse_and_finalize_number(): return 
            
            elif self._state == _ST_EXPECT_COMMA_OR_OBJ_END:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b','[0]: self._state = _ST_EXPECT_KEY_START; self._idx += 1
                elif byte == b'}'[0]: self._state = _ST_OBJ_END; self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_OBJ_END:
                if byte in _WHITESPACE: self._idx += 1; continue 
                self._state = _ST_ERROR; return 

            elif self._state == _ST_ERROR:
                return 

            else: 
                self._state = _ST_ERROR; return
        
        if self._idx > 0:
            self._buffer = self._buffer[self._idx:]
            self._idx = 0

# --- End of Refactored StreamingJsonParser ---

# --- Original Ultra-JSON-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class ParserState: # Original class
    """Immutable state container for the Ultra-JSON parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObjectParseState:
    """Immutable state for object parsing."""
    brace_count: int = 0
    in_string: bool = False
    escape_next: bool = False


class ByteValidator:
    """Stateless validator for Ultra-JSON-style byte processing."""

    @staticmethod
    def is_valid_key(key: str) -> bool:
        """Validate if a key is valid for high-performance processing."""
        return isinstance(key, str) and len(key) > 0

    @staticmethod
    def is_object_start_byte(byte_val: int) -> bool:
        """Check if byte represents object start."""
        return byte_val == ord('{')

    @staticmethod
    def is_object_end_byte(byte_val: int) -> bool:
        """Check if byte represents object end."""
        return byte_val == ord('}')

    @staticmethod
    def is_quote_byte(byte_val: int) -> bool:
        """Check if byte represents a quote."""
        return byte_val == ord('"')

    @staticmethod
    def is_escape_byte(byte_val: int) -> bool:
        """Check if byte represents an escape character."""
        return byte_val == ord('\\')


class PairExtractor: # Original class
    """Extracts complete key-value pairs from objects using stateless operations."""

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs for high-performance processing."""
        if not isinstance(obj, dict):
            return {}

        return {
            key: value
            for key, value in obj.items()
            if ByteValidator.is_valid_key(key)
        }


class ByteProcessor:
    """Stateless utility for high-performance byte processing."""

    @staticmethod
    def convert_to_bytes(buffer: str) -> bytearray:
        """Convert string buffer to bytes for faster processing."""
        return bytearray(buffer.encode('utf-8'))

    @staticmethod
    def find_byte_position(buffer: bytearray, start_pos: int, target_byte: int) -> int:
        """Find position of target byte in buffer."""
        for i in range(start_pos, len(buffer)):
            if buffer[i] == target_byte:
                return i
        return -1

    @staticmethod
    def safe_decode_bytes(obj_bytes: bytearray) -> str:
        """Safely decode bytes to string with error handling."""
        return obj_bytes.decode('utf-8', errors='replace')


class ObjectBoundaryFinder:
    """Finds object boundaries using Ultra-JSON-style fast scanning."""

    @staticmethod
    def find_object_boundaries(buffer: bytearray, start_pos: int) -> Optional[Tuple[int, int]]:
        """Find the boundaries of the next JSON object."""
        obj_start = ObjectBoundaryFinder._find_object_start(buffer, start_pos)
        if obj_start < 0:
            return None

        obj_end = ObjectBoundaryFinder._find_object_end(buffer, obj_start)
        if obj_end <= obj_start:
            return None

        return obj_start, obj_end

    @staticmethod
    def _find_object_start(buffer: bytearray, start_pos: int) -> int:
        """Fast scan for object start using byte scanning."""
        return ByteProcessor.find_byte_position(buffer, start_pos, ord('{'))

    @staticmethod
    def _find_object_end(buffer: bytearray, start_pos: int) -> int:
        """Fast scan for the object end with minimal overhead."""
        state = ObjectParseState()

        for i in range(start_pos, len(buffer)):
            byte_val = buffer[i]

            if ObjectBoundaryFinder._should_skip_byte(state, byte_val):
                continue

            ObjectBoundaryFinder._update_parse_state(state, byte_val)

            if ObjectBoundaryFinder._is_object_complete(state):
                return i

        return -1

    @staticmethod
    def _should_skip_byte(state: ObjectParseState, byte_val: int) -> bool:
        """Check if the current byte should be skipped during parsing."""
        if state.escape_next:
            state.escape_next = False
            return True

        if ByteValidator.is_escape_byte(byte_val):
            state.escape_next = True
            return True

        return False

    @staticmethod
    def _update_parse_state(state: ObjectParseState, byte_val: int) -> None:
        """Update parser state based on current byte."""
        if ByteValidator.is_quote_byte(byte_val) and not state.escape_next:
            state.in_string = not state.in_string
            return

        if not state.in_string:
            if ByteValidator.is_object_start_byte(byte_val):
                state.brace_count += 1
            elif ByteValidator.is_object_end_byte(byte_val):
                state.brace_count -= 1

    @staticmethod
    def _is_object_complete(state: ObjectParseState) -> bool:
        """Check if object parsing is complete."""
        return not state.in_string and state.brace_count == 0


class ObjectParser:
    """Parses individual objects using Ultra-JSON-style techniques."""

    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()

    def parse_object(self, obj_bytes: bytearray) -> Dict[str, Any]:
        """Parse object using Ultra-JSON style fast parsing."""
        parsed_obj = self._try_standard_json_parse(obj_bytes)
        if parsed_obj:
            return self._pair_extractor.extract_complete_pairs(parsed_obj)
        return self._try_partial_parse(obj_bytes)

    @staticmethod
    def _try_standard_json_parse(obj_bytes: bytearray) -> Optional[Dict[str, Any]]:
        """Attempt standard JSON parsing."""
        try:
            obj_str = obj_bytes.decode('utf-8')
            obj = json.loads(obj_str)
            return obj if isinstance(obj, dict) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _try_partial_parse(self, obj_bytes: bytearray) -> Dict[str, Any]:
        """Try partial parsing for incomplete objects."""
        try:
            obj_str = ByteProcessor.safe_decode_bytes(obj_bytes)
            balanced_obj = self._try_balance_and_parse(obj_str)
            if balanced_obj:
                return self._pair_extractor.extract_complete_pairs(balanced_obj)
            else:
                return self._extract_fields_fast(obj_str)
        except ValueError:
            return {}

    def _try_balance_and_parse(self, obj_str: str) -> Optional[Dict[str, Any]]:
        """Try to balance braces and parse the object."""
        brace_balance = self._calculate_brace_balance(obj_str)
        if brace_balance <= 0: return None
        balanced_str = obj_str + '}' * brace_balance
        try:
            obj = json.loads(balanced_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _calculate_brace_balance(obj_str: str) -> int:
        """Calculate the balance of opening vs. closing braces."""
        open_braces = obj_str.count('{')
        close_braces = obj_str.count('}')
        return open_braces - close_braces

    def _extract_fields_fast(self, obj_str: str) -> Dict[str, Any]:
        """Fast field extraction using minimal parsing."""
        try:
            extracted_fields = self._extract_key_value_pairs(obj_str)
            return extracted_fields if extracted_fields else {}
        except ValueError:
            return {}

    @staticmethod
    def _extract_key_value_pairs(obj_str: str) -> Dict[str, Any]:
        """Extract key-value pairs from string using fast parsing."""
        result = {}; position = 0
        while position < len(obj_str):
            key_info = ObjectParser._find_next_key(obj_str, position)
            if not key_info: break
            key, key_end_pos = key_info
            value_info = ObjectParser._find_value_for_key(obj_str, key_end_pos)
            if value_info:
                value, next_position = value_info
                result[key] = value; position = next_position
            else: position = key_end_pos + 1
        return result

    @staticmethod
    def _find_next_key(obj_str: str, start_pos: int) -> Optional[Tuple[str, int]]:
        """Find the next key in the JSON string."""
        quote_pos = obj_str.find('"', start_pos)
        if quote_pos == -1: return None
        key_start = quote_pos + 1
        key_end = obj_str.find('"', key_start)
        if key_end <= key_start: return None
        key = obj_str[key_start:key_end]
        return key, key_end

    @staticmethod
    def _find_value_for_key(obj_str: str, key_end_pos: int) -> Optional[Tuple[Any, int]]:
        """Find the value associated with a key."""
        colon_pos = obj_str.find(':', key_end_pos)
        if colon_pos == -1: return None
        value_start = ObjectParser._skip_whitespace(obj_str, colon_pos + 1)
        if value_start >= len(obj_str): return None
        value = ObjectParser._extract_value_fast(obj_str, value_start)
        if value is None: return None
        return value, value_start + 1 # This might need adjustment based on value length

    @staticmethod
    def _skip_whitespace(obj_str: str, start_pos: int) -> int:
        """Skip whitespace characters starting from position."""
        while start_pos < len(obj_str) and obj_str[start_pos].isspace():
            start_pos += 1
        return start_pos

    @staticmethod
    def _extract_value_fast(obj_str: str, start_pos: int) -> Any:
        """Fast value extraction with minimal overhead."""
        if start_pos >= len(obj_str): return None
        char = obj_str[start_pos]
        if char == '"': return ObjectParser._extract_string_value(obj_str, start_pos)
        elif char.isdigit() or char == '-': return ObjectParser._extract_number_value(obj_str, start_pos)
        else: return ObjectParser._extract_literal_value(obj_str, start_pos)

    @staticmethod
    def _extract_string_value(obj_str: str, start_pos: int) -> Optional[str]:
        """Extract string value from JSON."""
        end_pos = obj_str.find('"', start_pos + 1)
        return obj_str[start_pos + 1:end_pos] if end_pos > start_pos else None

    @staticmethod
    def _extract_number_value(obj_str: str, start_pos: int) -> Any:
        """Extract number value from JSON."""
        end_pos = start_pos + 1
        while (end_pos < len(obj_str) and
               (obj_str[end_pos].isdigit() or obj_str[end_pos] in '.-')):
            end_pos += 1
        num_str = obj_str[start_pos:end_pos]
        try: return int(num_str) if '.' not in num_str else float(num_str)
        except ValueError: return num_str

    @staticmethod
    def _extract_literal_value(obj_str: str, start_pos: int) -> Optional[Any]:
        """Extract literal values (true, false, null) from JSON."""
        remaining = obj_str[start_pos:].lower()
        if remaining.startswith('true'): return True
        elif remaining.startswith('false'): return False
        elif remaining.startswith('null'): return None
        return None


class UltraFastProcessor:
    """Main processor using Ultra-JSON-inspired high-performance techniques with dependency injection."""

    def __init__(self,
                 boundary_finder: ObjectBoundaryFinder = None,
                 object_parser: ObjectParser = None):
        self._boundary_finder = boundary_finder or ObjectBoundaryFinder()
        self._object_parser = object_parser or ObjectParser()
        self._parse_position = 0

    def process_buffer(self, buffer: str) -> Dict[str, Any]: # Original took str
        """Parse using Ultra-JSON inspired fast parsing techniques."""
        # This method is part of the original structure and is no longer directly
        # called by the refactored StreamingJsonParser.
        fast_buffer = ByteProcessor.convert_to_bytes(buffer)
        parsed_data = {}
        while self._has_more_data(fast_buffer):
            boundaries = self._boundary_finder.find_object_boundaries(fast_buffer, self._parse_position)
            if not boundaries: break
            obj_start, obj_end = boundaries
            if self._is_complete_object(obj_start, obj_end):
                obj_data = self._process_complete_object(fast_buffer, obj_start, obj_end)
                parsed_data.update(obj_data)
                self._parse_position = obj_end + 1
            else: break
        return parsed_data

    def _has_more_data(self, buffer: bytearray) -> bool:
        """Check if there's more data to parse."""
        return self._parse_position < len(buffer)

    @staticmethod
    def _is_complete_object(obj_start: int, obj_end: int) -> bool:
        """Check if object boundaries represent a complete object."""
        return obj_end > obj_start

    def _process_complete_object(self, buffer: bytearray, obj_start: int, obj_end: int) -> Dict[str, Any]:
        """Process a complete JSON object."""
        obj_bytes = buffer[obj_start:obj_end + 1]
        return self._object_parser.parse_object(obj_bytes)

# Mandatory tests for the refactored StreamingJsonParser
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

if __name__ == '__main__':
    test_streaming_json_parser()
    test_chunked_streaming_json_parser()
    test_partial_streaming_json_parser()
    print("Refactored StreamingJsonParser tests passed successfully!")
