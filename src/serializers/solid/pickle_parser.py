"""
Pickle streaming parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by Pickle object serialization.
The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original Pickle-inspired helper classes remain but are no longer used by StreamingJsonParser.
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
    This version replaces the original Pickle-style parser in this module.
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

# --- Original Pickle-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class ParserState: # Original class
    """Immutable state container for the Pickle parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StringState:
    """Immutable state for string parsing."""
    in_string: bool = False
    escape_next: bool = False

    def process_char(self, char: str) -> 'StringState':
        """Process character and return new state."""
        if self.escape_next:
            return StringState(self.in_string, False)

        if CharacterValidator.is_escape_char(char):
            return StringState(self.in_string, True)

        if CharacterValidator.is_quote_char(char):
            return StringState(not self.in_string, False)

        return StringState(self.in_string, False)


class CharacterValidator:
    """Stateless validator for Pickle-style character processing."""

    @staticmethod
    def is_valid_key(key: str) -> bool:
        """Check if the key is valid and complete."""
        return isinstance(key, str) and len(key) > 0

    @staticmethod
    def is_escape_char(char: str) -> bool:
        """Check if character is an escape character."""
        return char == '\\'

    @staticmethod
    def is_quote_char(char: str) -> bool:
        """Check if the character is a quote."""
        return char == '"'

    @staticmethod
    def is_open_brace(char: str) -> bool:
        """Check if character is an opening brace."""
        return char == '{'

    @staticmethod
    def is_close_brace(char: str) -> bool:
        """Check if character is a closing brace."""
        return char == '}'


class PairExtractor: # Original class
    """Extracts complete key-value pairs from objects using stateless operations."""

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        if not isinstance(obj, dict):
            return {}

        return {
            key: value
            for key, value in obj.items()
            if CharacterValidator.is_valid_key(key)
        }


class BraceCounter:
    """Stateless utility for brace counting."""

    @staticmethod
    def update_count(char: str, current_count: int, in_string: bool) -> int:
        """Update brace count based on character."""
        if in_string:
            return current_count

        if CharacterValidator.is_open_brace(char):
            return current_count + 1
        elif CharacterValidator.is_close_brace(char):
            return current_count - 1

        return current_count

    @staticmethod
    def is_balanced(count: int) -> bool:
        """Check if braces are balanced."""
        return count == 0


class ObjectBoundaryFinder:
    """Finds object boundaries using Pickle-inspired techniques."""

    @staticmethod
    def find_object_end(json_str: str) -> int:
        """Find the end position of a complete JSON object."""
        brace_count = 0
        string_state = StringState()

        for i, char in enumerate(json_str):
            string_state = string_state.process_char(char)
            brace_count = BraceCounter.update_count(char, brace_count, string_state.in_string)

            if BraceCounter.is_balanced(brace_count) and i > 0:
                return i

        return -1

    @staticmethod
    def find_string_end(json_str: str) -> int:
        """Find the end position of a string."""
        if not ObjectBoundaryFinder._starts_with_quote(json_str):
            return -1

        return ObjectBoundaryFinder._find_closing_quote(json_str)

    @staticmethod
    def _starts_with_quote(json_str: str) -> bool:
        """Check if string starts with quote."""
        return json_str.startswith('"')

    @staticmethod
    def _find_closing_quote(json_str: str) -> int:
        """Find the closing quote position."""
        escape_next = False

        for i in range(1, len(json_str)):
            char = json_str[i]

            if escape_next:
                escape_next = False
                continue

            if CharacterValidator.is_escape_char(char):
                escape_next = True
                continue

            if CharacterValidator.is_quote_char(char):
                return i

        return -1


class JsonValidator:
    """Stateless utility for JSON validation."""

    @staticmethod
    def is_valid_dict(obj: Any) -> bool:
        """Check if an object is a valid dictionary."""
        return isinstance(obj, dict)

    @staticmethod
    def has_content(data: Dict[str, Any]) -> bool:
        """Check if the dictionary has content."""
        return bool(data)


class BraceBalancer:
    """Stateless utility for brace balancing."""

    @staticmethod
    def count_braces(text: str) -> Tuple[int, int]:
        """Count open and close braces."""
        return text.count('{'), text.count('}')

    @staticmethod
    def needs_balancing(open_count: int, close_count: int) -> bool:
        """Check if braces need balancing."""
        return open_count > close_count

    @staticmethod
    def balance_string(text: str, open_count: int, close_count: int) -> str:
        """Balance braces in string."""
        missing_braces = open_count - close_count
        return text + '}' * missing_braces


class ObjectParser: # Original class
    """Parses JSON objects using Pickle-inspired techniques."""

    def __init__(self,
                 boundary_finder: ObjectBoundaryFinder = None,
                 pair_extractor: PairExtractor = None):
        self._boundary_finder = boundary_finder or ObjectBoundaryFinder()
        self._pair_extractor = pair_extractor or PairExtractor()

    def parse_object_at_position(self, buffer: str, position: int) -> Dict[str, Any]:
        """Parse JSON object starting at given position."""
        try:
            remaining = buffer[position:]
            obj_end = self._boundary_finder.find_object_end(remaining)

            if obj_end > 0:
                return self._parse_complete_object(remaining, obj_end)

        except ValueError:
            pass

        return {}

    def _parse_complete_object(self, remaining: str, obj_end: int) -> Dict[str, Any]:
        """Parse a complete JSON object."""
        json_str = remaining[:obj_end + 1]

        try:
            obj = json.loads(json_str)
            if JsonValidator.is_valid_dict(obj):
                return self._pair_extractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass

        return {}


class PartialParser:
    """Handles partial JSON parsing using Pickle-inspired reconstruction."""

    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()

    def try_partial_parse(self, buffer: str, position: int) -> Dict[str, Any]:
        """Try to parse partial JSON objects."""
        remaining = buffer[position:]

        for end_pos in range(len(remaining), 0, -1):
            test_str = remaining[:end_pos]
            result = self._try_parse_substring(test_str)
            if result:
                return result

        return {}

    def _try_parse_substring(self, test_str: str) -> Dict[str, Any]:
        """Try to parse a substring."""
        balanced_str = self._balance_braces(test_str)
        if not balanced_str:
            return {}

        parsed_obj = self._try_parse_json(balanced_str)
        if not parsed_obj:
            return {}

        return self._pair_extractor.extract_complete_pairs(parsed_obj)

    @staticmethod
    def _balance_braces(test_str: str) -> Optional[str]:
        """Balance braces in a JSON string."""
        open_count, close_count = BraceBalancer.count_braces(test_str)

        if BraceBalancer.needs_balancing(open_count, close_count):
            return BraceBalancer.balance_string(test_str, open_count, close_count)

        return None # Original returned None, not test_str

    @staticmethod
    def _try_parse_json(json_str: str) -> Optional[Dict[str, Any]]:
        """Try to parse JSON string."""
        try:
            obj = json.loads(json_str)
            return obj if JsonValidator.is_valid_dict(obj) else None
        except json.JSONDecodeError:
            return None


class StringHandler:
    """Handles string processing using Pickle-inspired techniques."""

    def __init__(self, boundary_finder: ObjectBoundaryFinder = None):
        self._boundary_finder = boundary_finder or ObjectBoundaryFinder()

    def handle_string_start(self, buffer: str, position: int) -> bool:
        """Handle the start of string value."""
        try:
            remaining = buffer[position:]
            string_end = self._boundary_finder.find_string_end(remaining)
            return string_end > 0
        except (IndexError, AttributeError, TypeError):
            return False


class SingleThreadedProcessor:
    """Single-threaded processor for Pickle-inspired parsing with dependency injection."""

    def __init__(self,
                 object_parser: ObjectParser = None,
                 string_handler: StringHandler = None,
                 partial_parser: PartialParser = None):
        self._object_parser = object_parser or ObjectParser()
        self._string_handler = string_handler or StringHandler()
        self._partial_parser = partial_parser or PartialParser()

    def parse_single_threaded(self, buffer: str) -> Dict[str, Any]: # Original took str
        """Parse using single-threaded Pickle-inspired strategy."""
        # This method is part of the original structure and is no longer directly
        # called by the refactored StreamingJsonParser.
        parsed_data = {}
        for i, char in enumerate(buffer):
            new_data = self._process_character(char, buffer, i)
            if JsonValidator.has_content(new_data):
                parsed_data.update(new_data)
        return parsed_data

    def _process_character(self, char: str, buffer: str, position: int) -> Dict[str, Any]:
        """Process a single character."""
        if CharacterValidator.is_open_brace(char):
            return self._handle_open_brace(buffer, position)
        elif CharacterValidator.is_quote_char(char):
            self._handle_quote(buffer, position)
        return {}

    def _handle_open_brace(self, buffer: str, position: int) -> Dict[str, Any]:
        """Handle opening brace with fallback."""
        new_data = self._object_parser.parse_object_at_position(buffer, position)
        if not JsonValidator.has_content(new_data):
            new_data = self._partial_parser.try_partial_parse(buffer, position)
        return new_data

    def _handle_quote(self, buffer: str, position: int) -> None:
        """Handle quote character."""
        self._string_handler.handle_string_start(buffer, position)

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
