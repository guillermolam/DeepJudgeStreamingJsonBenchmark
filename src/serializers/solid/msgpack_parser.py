"""
MsgPack streaming parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by MsgPack compact binary encoding.
The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original MsgPack-inspired helper classes remain but are no longer used by StreamingJsonParser.
"""
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, List, Tuple

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
    This version replaces the original MsgPack-style parser in this module.
    """

    def __init__(self):
        """Initializes the streaming JSON parser."""
        self._buffer = bytearray()
        self._result: Dict[str, Any] = {}
        self._state = _ST_EXPECT_OBJ_START

        self._current_key_bytes = bytearray()
        self._current_value_bytes = bytearray()

        self._active_key: str | None = None
        self._idx = 0

    def consume(self, chunk: str) -> None: # Changed to accept str
        """
        Appends a chunk of JSON string to the internal buffer and processes it
        after converting to bytes.

        Args:
            chunk: A string containing a part of the JSON document.
        """
        if not isinstance(chunk, str):
            return

        byte_chunk = chunk.encode('utf-8', errors='replace')
        self._buffer.extend(byte_chunk)
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
        if byte_val == b'"'[0]:
            return b'"'[0]
        if byte_val == b'\\'[0]:
            return b'\\'[0]
        if byte_val == b'/'[0]:
            return b'/'[0]
        if byte_val == b'b'[0]:
            return b'\b'[0]
        if byte_val == b'f'[0]:
            return b'\f'[0]
        if byte_val == b'n'[0]:
            return b'\n'[0]
        if byte_val == b'r'[0]:
            return b'\r'[0]
        if byte_val == b't'[0]:
            return b'\t'[0]
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
            self._state = _ST_ERROR
            return False

        num_str = self._current_value_bytes.decode('utf-8')

        if num_str == "-" or num_str == "+" or num_str.endswith(('.', 'e', 'E', '+', '-')):
            self._state = _ST_ERROR
            return False

        try:
            if any(c in num_str for c in ('.', 'e', 'E')):
                parsed_num = float(num_str)
            else:
                parsed_num = int(num_str)
            self._finalize_value(parsed_num)
            return True
        except ValueError:
            self._state = _ST_ERROR
            return False

    def _process_buffer(self):
        """Processes the internal buffer to parse JSON content using a state machine."""
        buffer_len = len(self._buffer)
        while self._idx < buffer_len:
            byte = self._buffer[self._idx]

            if self._state == _ST_EXPECT_OBJ_START:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b'{'[0]:
                    self._state = _ST_EXPECT_KEY_START
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_EXPECT_KEY_START:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b'"'[0]:
                    self._state = _ST_IN_KEY
                    self._current_key_bytes.clear()
                    self._active_key = None
                    self._idx += 1
                elif byte == b'}'[0]:
                    self._state = _ST_OBJ_END
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_KEY:
                if byte == b'\\'[0]:
                    self._state = _ST_IN_KEY_ESCAPE
                    self._idx += 1
                elif byte == b'"'[0]:
                    try:
                        self._active_key = self._current_key_bytes.decode('utf-8')
                        self._state = _ST_EXPECT_COLON
                    except UnicodeDecodeError:
                        self._active_key = None
                        self._state = _ST_ERROR
                        return
                    self._idx += 1
                else:
                    self._current_key_bytes.append(byte)
                    self._idx += 1

            elif self._state == _ST_IN_KEY_ESCAPE:
                self._current_key_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_KEY
                self._idx += 1

            elif self._state == _ST_EXPECT_COLON:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b':'[0]:
                    self._state = _ST_EXPECT_VALUE_START
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_EXPECT_VALUE_START:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                self._current_value_bytes.clear()
                if byte == b'"'[0]:
                    self._state = _ST_IN_STRING_VALUE
                    self._idx += 1
                elif byte == b't'[0]:
                    self._state = _ST_IN_TRUE
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                elif byte == b'f'[0]:
                    self._state = _ST_IN_FALSE
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                elif byte == b'n'[0]:
                    self._state = _ST_IN_NULL
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                elif byte in _NUMBER_CHARS and (byte != b'+'[0]):
                    self._state = _ST_IN_NUMBER
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_STRING_VALUE:
                if byte == b'\\'[0]:
                    self._state = _ST_IN_STRING_VALUE_ESCAPE
                    self._idx += 1
                elif byte == b'"'[0]:
                    if self._active_key is not None:
                        try:
                            value_str = self._current_value_bytes.decode('utf-8')
                            self._finalize_value(value_str)
                        except UnicodeDecodeError:
                            value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                            self._finalize_value(value_str)
                    else:
                        self._state = _ST_ERROR
                        return
                    self._idx += 1
                else:
                    self._current_value_bytes.append(byte)
                    self._idx += 1

            elif self._state == _ST_IN_STRING_VALUE_ESCAPE:
                self._current_value_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_STRING_VALUE
                self._idx += 1

            elif self._state == _ST_IN_TRUE:
                self._current_value_bytes.append(byte)
                self._idx += 1
                if self._current_value_bytes == b"true":
                    self._finalize_value(True)
                elif not b"true".startswith(self._current_value_bytes):
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_FALSE:
                self._current_value_bytes.append(byte)
                self._idx += 1
                if self._current_value_bytes == b"false":
                    self._finalize_value(False)
                elif not b"false".startswith(self._current_value_bytes):
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_NULL:
                self._current_value_bytes.append(byte)
                self._idx += 1
                if self._current_value_bytes == b"null":
                    self._finalize_value(None)
                elif not b"null".startswith(self._current_value_bytes):
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_NUMBER:
                if byte in _NUMBER_CHARS:
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                else:
                    if not self._parse_and_finalize_number():
                        return

            elif self._state == _ST_EXPECT_COMMA_OR_OBJ_END:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b','[0]:
                    self._state = _ST_EXPECT_KEY_START
                    self._idx += 1
                elif byte == b'}'[0]:
                    self._state = _ST_OBJ_END
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_OBJ_END:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                self._state = _ST_ERROR
                return

            elif self._state == _ST_ERROR:
                return

            else:
                self._state = _ST_ERROR
                return

        if self._idx > 0:
            self._buffer = self._buffer[self._idx:]
            self._idx = 0

# --- End of Refactored StreamingJsonParser ---

# --- Original MsgPack-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class ParserState: # Original class
    """Immutable state container for the MsgPack parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


class MsgPackFormatCode(Enum):
    """MsgPack format codes (simplified for type detection)."""
    FIXMAP = 0x80
    FIXARRAY = 0x90
    FIXSTR = 0xa0
    NIL = 0xc0
    FALSE = 0xc2
    TRUE = 0xc3
    FLOAT32 = 0xca
    FLOAT64 = 0xcb
    UINT8 = 0xcc
    UINT16 = 0xcd
    UINT32 = 0xce
    UINT64 = 0xcf


@dataclass
class MessageParseState:
    """Immutable state for message parsing."""
    brace_count: int = 0
    in_string: bool = False
    escape_next: bool = False


class CharacterProcessor:
    """Stateless utility for processing individual characters."""
    @staticmethod
    def should_skip_character(state: MessageParseState, char: str) -> Tuple[bool, MessageParseState]:
        if state.escape_next:
            return True, MessageParseState(state.brace_count, state.in_string, False)
        if char == '\\':
            return True, MessageParseState(state.brace_count, state.in_string, True)
        return False, state

    @staticmethod
    def update_string_state(state: MessageParseState, char: str) -> MessageParseState:
        if char == '"' and not state.escape_next:
            return MessageParseState(state.brace_count, not state.in_string, state.escape_next)
        return state

    @staticmethod
    def update_brace_count(state: MessageParseState, char: str) -> Tuple[bool, MessageParseState]:
        if char == '{':
            new_state = MessageParseState(state.brace_count + 1, state.in_string, state.escape_next)
            return True, new_state
        elif char == '}':
            new_state = MessageParseState(state.brace_count - 1, state.in_string, state.escape_next)
            return True, new_state
        return False, state


class MessageValidator: # Original class
    """Stateless utility for message validation."""
    @staticmethod
    def is_complete_message(state: MessageParseState, message: str) -> bool:
        return state.brace_count == 0 and message.strip()

    @staticmethod
    def should_include_incomplete(message: str, state: MessageParseState) -> bool:
        return message.strip() and state.brace_count > 0


class MessageExtractor: # Original class
    """Extracts MsgPack-style messages from text data using stateless operations."""
    @staticmethod
    def extract_messages(text_data: str) -> List[str]:
        messages: List[str] = []
        current_message: str = ""
        state = MessageParseState()
        for char_idx, char in enumerate(text_data): # char_idx was unused
            current_message += char
            prev_brace_count = state.brace_count
            state = MessageExtractor._process_single_character(char, state)

            if not state.in_string and prev_brace_count > 0 and state.brace_count == 0 and current_message.strip():
                 messages.append(current_message.strip())
                 current_message = ""
        MessageExtractor._handle_final_message(messages, current_message, state)
        return messages

    @staticmethod
    def _process_single_character(char: str, state: MessageParseState) -> MessageParseState:
        should_skip, new_state = CharacterProcessor.should_skip_character(state, char)
        if should_skip:
            return new_state
        new_state = CharacterProcessor.update_string_state(new_state, char)
        if not new_state.in_string:
            _, new_state = CharacterProcessor.update_brace_count(new_state, char)
        return new_state

    @staticmethod
    def _handle_final_message(messages: List[str], current_message: str, state: MessageParseState) -> None:
        if MessageValidator.should_include_incomplete(current_message, state):
            messages.append(current_message.strip())


class FormatCorrector:
    """Stateless utility for correcting message format using MsgPack-inspired rules."""
    @staticmethod
    def correct_format(message: str) -> Optional[str]:
        try:
            brace_info = FormatCorrector._analyze_braces(message)
            if brace_info is None:
                return None
            open_braces, close_braces = brace_info
            return FormatCorrector._apply_correction(message, open_braces, close_braces)
        except ValueError:
            return None

    @staticmethod
    def _analyze_braces(message: str) -> Optional[Tuple[int, int]]:
        open_braces = message.count('{')
        close_braces = message.count('}')
        if open_braces == 0:
            return None
        return open_braces, close_braces

    @staticmethod
    def _apply_correction(message: str, open_braces: int, close_braces: int) -> Optional[str]:
        if open_braces > close_braces:
            return message + '}' * (open_braces - close_braces)
        elif open_braces == close_braces:
            return message
        return None


class TypeDetector:
    """Stateless utility for MsgPack-inspired type detection."""
    @staticmethod
    def is_string_type(value_str: str) -> bool:
        return value_str.startswith('"') and value_str.endswith('"')
    @staticmethod
    def is_boolean_type(value_str: str) -> Optional[bool]:
        lower_val = value_str.lower()
        if lower_val == 'true':
            return True
        elif lower_val == 'false':
            return False
        return None
    @staticmethod
    def is_null_type(value_str: str) -> bool:
        return value_str.lower() == 'null'
    @staticmethod
    def is_integer_type(value_str: str) -> Optional[int]:
        if value_str.isdigit():
            return int(value_str)
        elif value_str.startswith('-') and value_str[1:].isdigit():
            return int(value_str)
        return None
    @staticmethod
    def is_float_type(value_str: str) -> Optional[float]:
        if '.' in value_str:
            try:
                return float(value_str)
            except ValueError:
                return None
        return None


class ValueParser: # Original class
    """Parses values using MsgPack-inspired type detection with stateless operations."""
    @staticmethod
    def parse_value(value_str: str) -> Any:
        try:
            cleaned_value = value_str.rstrip(',}')
            return ValueParser._try_parse_by_type(cleaned_value)
        except ValueError:
            return None

    @staticmethod
    def _try_parse_by_type(value_str: str) -> Any:
        string_result = ValueParser._try_parse_string(value_str)
        if string_result is not None:
            return string_result
        literal_result = ValueParser._try_parse_literals(value_str)
        if literal_result is not None:
            return literal_result
        numeric_result = ValueParser._try_parse_numeric(value_str)
        if numeric_result is not None:
            return numeric_result
        return value_str

    @staticmethod
    def _try_parse_string(value_str: str) -> Optional[str]:
        if TypeDetector.is_string_type(value_str):
            return value_str[1:-1]
        return None
    @staticmethod
    def _try_parse_literals(value_str: str) -> Any:
        bool_result = TypeDetector.is_boolean_type(value_str)
        if bool_result is not None:
            return bool_result
        if TypeDetector.is_null_type(value_str):
            return None
        return None
    @staticmethod
    def _try_parse_numeric(value_str: str) -> Optional[Any]:
        int_result = TypeDetector.is_integer_type(value_str)
        if int_result is not None:
            return int_result
        float_result = TypeDetector.is_float_type(value_str)
        if float_result is not None:
            return float_result
        return None


class LineProcessor:
    """Stateless utility for processing individual lines."""
    @staticmethod
    def is_valid_field_line(line: str) -> bool:
        return ':' in line and '"' in line
    @staticmethod
    def extract_key_value_from_line(line: str) -> Optional[Tuple[str, str]]:
        colon_pos = line.find(':')
        if colon_pos <= 0:
            return None
        key_part = line[:colon_pos].strip()
        value_part = line[colon_pos + 1:].strip()
        if not (key_part.startswith('"') and key_part.endswith('"')):
            return None
        key = key_part[1:-1]
        return key, value_part


class FieldExtractor: # Original class
    """Extracts fields using MsgPack-style field parsing with dependency injection."""
    def __init__(self, value_parser: ValueParser = None):
        self._value_parser = value_parser or ValueParser()

    def extract_fields(self, message: str) -> Dict[str, Any]:
        try:
            result = {}
            lines = message.split('\n')
            for line in lines:
                line = line.strip()
                if LineProcessor.is_valid_field_line(line):
                    key_value_pair = self._process_field_line(line)
                    if key_value_pair:
                        key, value = key_value_pair
                        result[key] = value
            return result
        except ValueError:
            return {}

    def _process_field_line(self, line: str) -> Optional[Tuple[str, Any]]:
        line_parts = LineProcessor.extract_key_value_from_line(line)
        if line_parts is None:
            return None
        key, value_part = line_parts
        value = self._value_parser.parse_value(value_part)
        if value is not None:
            return key, value
        return None


class ValueValidator:
    """Stateless utility for validating values according to MsgPack rules."""
    @staticmethod
    def is_valid_msgpack_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return ValueValidator._is_valid_array(value)
        if isinstance(value, dict):
            return ValueValidator._is_valid_map(value)
        return False
    @staticmethod
    def _is_valid_array(array: List[Any]) -> bool:
        return all(ValueValidator.is_valid_msgpack_value(item) for item in array)
    @staticmethod
    def _is_valid_map(mapping: Dict[str, Any]) -> bool:
        return all(isinstance(k, str) and ValueValidator.is_valid_msgpack_value(v) for k, v in mapping.items())


class PairValidator:
    """Validates key-value pairs with MsgPack-style validation using stateless operations."""
    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in obj.items() if PairValidator._is_valid_pair(key, value)}
    @staticmethod
    def _is_valid_pair(key: str, value: Any) -> bool:
        return (PairValidator._is_valid_key(key) and ValueValidator.is_valid_msgpack_value(value))
    @staticmethod
    def _is_valid_key(key: str) -> bool:
        return isinstance(key, str) and len(key) > 0


class MessageProcessor: # Original class
    """Processes MsgPack-style messages with dependency injection."""
    def __init__(self, format_corrector: FormatCorrector = None, value_parser: ValueParser = None,
                 field_extractor: FieldExtractor = None, pair_validator: PairValidator = None):
        self._format_corrector = format_corrector or FormatCorrector()
        self._value_parser = value_parser or ValueParser()
        self._field_extractor = field_extractor or FieldExtractor(self._value_parser)
        self._pair_validator = pair_validator or PairValidator()

    def process_messages(self, messages: List[str]) -> Dict[str, Any]:
        parsed_data = {}
        for message in messages:
            message_data = self._decode_single_message(message)
            if message_data:
                parsed_data.update(message_data)
        return parsed_data

    def _decode_single_message(self, message: str) -> Optional[Dict[str, Any]]:
        direct_result = self._try_direct_json_parse(message)
        if direct_result:
            return direct_result
        return self._try_partial_decode(message)

    def _try_direct_json_parse(self, message: str) -> Optional[Dict[str, Any]]:
        try:
            obj = json.loads(message)
            if isinstance(obj, dict):
                return self._pair_validator.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass
        return None

    def _try_partial_decode(self, message: str) -> Optional[Dict[str, Any]]:
        try:
            if '{' not in message:
                return None
            corrected_message = self._format_corrector.correct_format(message)
            if corrected_message:
                return self._process_corrected_message(corrected_message, message)
            return None
        except ValueError:
            return None

    def _process_corrected_message(self, corrected_message: str, original_message: str) -> Optional[Dict[str, Any]]:
        try:
            obj = json.loads(corrected_message)
            if isinstance(obj, dict):
                return self._pair_validator.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            return self._field_extractor.extract_fields(original_message)
        return None


class BinaryStreamProcessor: # Original class
    """Processes binary stream for MsgPack-style processing with dependency injection."""
    def __init__(self, message_extractor: MessageExtractor = None, message_processor: MessageProcessor = None):
        self._message_extractor = message_extractor or MessageExtractor()
        self._message_processor = message_processor or MessageProcessor()
        self._binary_stream = bytearray()

    def process_buffer(self, buffer: str) -> Dict[str, Any]: # Original took str
        """Process buffer using MsgPack-style processing."""
        # This method is part of the original structure and is no longer directly
        # called by the refactored StreamingJsonParser.
        buffer_bytes = buffer.encode('utf-8')
        self._binary_stream.extend(buffer_bytes)
        return self._parse_msgpack_style()

    def _parse_msgpack_style(self) -> Dict[str, Any]:
        """Parse using MsgPack-inspired compact encoding."""
        try:
            text_data = self._binary_stream.decode('utf-8', errors='ignore')
            messages = self._message_extractor.extract_messages(text_data)
            return self._message_processor.process_messages(messages)
        except ValueError:
            return {}

# Mandatory tests for the refactored StreamingJsonParser
def test_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}') # Changed to str
    assert parser.get() == {"foo": "bar"}

def test_chunked_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": ') # Changed to str
    parser.consume('"bar"}') # Changed to str
    assert parser.get() == {"foo": "bar"}

def test_partial_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar') # Changed to str
    assert parser.get() == {"foo": "bar"}

if __name__ == '__main__':
    test_streaming_json_parser()
    test_chunked_streaming_json_parser()
    test_partial_streaming_json_parser()
    print("Refactored StreamingJsonParser tests passed successfully!")
