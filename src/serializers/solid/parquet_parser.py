"""
Parquet streaming parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by Parquet columnar storage format.
The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original Parquet-inspired helper classes remain but are no longer used by StreamingJsonParser.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Union

# --- Start of Refactored StreamingJsonParser and its dependencies ---

# State constants for the parser
_ST_EXPECT_OBJ_START = 0
_ST_EXPECT_KEY_START = 1
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
    This version replaces the original Parquet-style parser in this module.
    """

    def __init__(self):
        """Initializes the streaming JSON parser."""
        self._buffer = bytearray()
        self._result: Dict[str, Any] = {}
        self._state = _ST_EXPECT_OBJ_START

        self._current_key_bytes = bytearray()
        self._current_value_bytes = bytearray()

        self._active_key: Optional[str] = None
        self._idx = 0

        self._state_handlers = {
            _ST_EXPECT_OBJ_START: self._handle_expect_obj_start,
            _ST_EXPECT_KEY_START: self._handle_expect_key_start,
            _ST_IN_KEY: self._handle_in_key,
            _ST_IN_KEY_ESCAPE: self._handle_in_key_escape,
            _ST_EXPECT_COLON: self._handle_expect_colon,
            _ST_EXPECT_VALUE_START: self._handle_expect_value_start,
            _ST_IN_STRING_VALUE: self._handle_in_string_value,
            _ST_IN_STRING_VALUE_ESCAPE: self._handle_in_string_value_escape,
            _ST_IN_TRUE: self._handle_in_true,
            _ST_IN_FALSE: self._handle_in_false,
            _ST_IN_NULL: self._handle_in_null,
            _ST_IN_NUMBER: self._handle_in_number,
            _ST_EXPECT_COMMA_OR_OBJ_END: self._handle_expect_comma_or_obj_end,
            _ST_OBJ_END: self._handle_obj_end,
        }

    def consume(self, chunk: str) -> None:
        """
        Appends a chunk of JSON string to the internal buffer and processes it
        after converting to bytes.
        """
        if not isinstance(chunk, str):
            return
        byte_chunk = chunk.encode('utf-8', errors='replace')
        self._buffer.extend(byte_chunk)
        self._process_buffer()

    def get(self) -> Dict[str, Any]:
        """
        Returns the current state of the parsed JSON object.
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
        escape_map = {
            b'"'[0]: b'"'[0],
            b'\\'[0]: b'\\'[0],
            b'/'[0]: b'/'[0],
            b'b'[0]: b'\b'[0],
            b'f'[0]: b'\f'[0],
            b'n'[0]: b'\n'[0],
            b'r'[0]: b'\r'[0],
            b't'[0]: b'\t'[0],
        }
        return escape_map.get(byte_val, byte_val)

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
        if self._is_invalid_number(num_str):
            self._state = _ST_ERROR
            return False

        return self._convert_and_finalize_number(num_str)

    def _is_invalid_number(self, num_str: str) -> bool:
        """Checks if the number string is invalid."""
        return num_str in ("-", "+") or num_str.endswith(('.', 'e', 'E', '+', '-'))

    def _convert_and_finalize_number(self, num_str: str) -> bool:
        """Converts the number string to a number and finalizes it."""
        try:
            is_float = '.' in num_str or 'e' in num_str or 'E' in num_str
            parsed_num = float(num_str) if is_float else int(num_str)
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
            handler = self._state_handlers.get(self._state)
            if handler:
                handler(byte)
            else:
                self._state = _ST_ERROR
                return

        if self._idx > 0:
            self._buffer = self._buffer[self._idx:]
            self._idx = 0

    def _handle_expect_obj_start(self, byte: int):
        if byte in _WHITESPACE:
            self._idx += 1
        elif byte == b'{'[0]:
            self._state = _ST_EXPECT_KEY_START
            self._idx += 1
        else:
            self._state = _ST_ERROR

    def _handle_expect_key_start(self, byte: int):
        if byte in _WHITESPACE:
            self._idx += 1
        elif byte == b'"'[0]:
            self._state = _ST_IN_KEY
            self._current_key_bytes.clear()
            self._active_key = None
            self._idx += 1
        elif byte == b'}'[0]:
            self._state = _ST_OBJ_END
            self._idx += 1
        else:
            self._state = _ST_ERROR

    def _handle_in_key(self, byte: int):
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
            self._idx += 1
        else:
            self._current_key_bytes.append(byte)
            self._idx += 1

    def _handle_in_key_escape(self, byte: int):
        self._current_key_bytes.append(self._handle_escape_char(byte))
        self._state = _ST_IN_KEY
        self._idx += 1

    def _handle_expect_colon(self, byte: int):
        if byte in _WHITESPACE:
            self._idx += 1
        elif byte == b':'[0]:
            self._state = _ST_EXPECT_VALUE_START
            self._idx += 1
        else:
            self._state = _ST_ERROR

    def _handle_expect_value_start(self, byte: int):
        if byte in _WHITESPACE:
            self._idx += 1
            return

        self._current_value_bytes.clear()
        value_start_map = {
            b'"'[0]: _ST_IN_STRING_VALUE,
            b't'[0]: _ST_IN_TRUE,
            b'f'[0]: _ST_IN_FALSE,
            b'n'[0]: _ST_IN_NULL,
        }
        
        if byte in value_start_map:
            self._state = value_start_map[byte]
            if self._state != _ST_IN_STRING_VALUE:
                self._current_value_bytes.append(byte)
        elif byte in _NUMBER_CHARS and byte != b'+'[0]:
            self._state = _ST_IN_NUMBER
            self._current_value_bytes.append(byte)
        else:
            self._state = _ST_ERROR
            return
        self._idx += 1

    def _handle_in_string_value(self, byte: int):
        if byte == b'\\'[0]:
            self._state = _ST_IN_STRING_VALUE_ESCAPE
            self._idx += 1
        elif byte == b'"'[0]:
            if self._active_key is not None:
                try:
                    value_str = self._current_value_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                self._finalize_value(value_str)
            else:
                self._state = _ST_ERROR
            self._idx += 1
        else:
            self._current_value_bytes.append(byte)
            self._idx += 1

    def _handle_in_string_value_escape(self, byte: int):
        self._current_value_bytes.append(self._handle_escape_char(byte))
        self._state = _ST_IN_STRING_VALUE
        self._idx += 1

    def _handle_boolean_or_null(self, byte: int, expected_bytes: bytes, final_value: Any):
        self._current_value_bytes.append(byte)
        self._idx += 1
        if self._current_value_bytes == expected_bytes:
            self._finalize_value(final_value)
        elif not expected_bytes.startswith(self._current_value_bytes):
            self._state = _ST_ERROR

    def _handle_in_true(self, byte: int):
        self._handle_boolean_or_null(byte, b"true", True)

    def _handle_in_false(self, byte: int):
        self._handle_boolean_or_null(byte, b"false", False)

    def _handle_in_null(self, byte: int):
        self._handle_boolean_or_null(byte, b"null", None)

    def _handle_in_number(self, byte: int):
        if byte in _NUMBER_CHARS:
            self._current_value_bytes.append(byte)
            self._idx += 1
        else:
            if not self._parse_and_finalize_number():
                return

    def _handle_expect_comma_or_obj_end(self, byte: int):
        if byte in _WHITESPACE:
            self._idx += 1
        elif byte == b','[0]:
            self._state = _ST_EXPECT_KEY_START
            self._idx += 1
        elif byte == b'}'[0]:
            self._state = _ST_OBJ_END
            self._idx += 1
        else:
            self._state = _ST_ERROR

    def _handle_obj_end(self, byte: int):
        if byte in _WHITESPACE:
            self._idx += 1
        else:
            self._state = _ST_ERROR

# --- End of Refactored StreamingJsonParser ---

# --- Original Parquet-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class ParserState: # Original class
    """Immutable state container for the Parquet parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedMessage:
    """Immutable data structure for parsed messages."""
    content: str
    is_complete: bool
    brace_count: int


class MessageValidator:
    """Stateless validator for Parquet-style messages."""

    @staticmethod
    def is_valid_key(key: str) -> bool:
        """Validate if a key is valid for columnar storage."""
        return isinstance(key, str) and len(key) > 0

    @staticmethod
    def is_valid_value(value: Any) -> bool:
        """Check if the value is valid for columnar storage."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(MessageValidator.is_valid_value(item) for item in value)
        if isinstance(value, dict):
            return all(
                isinstance(k, str) and MessageValidator.is_valid_value(v)
                for k, v in value.items()
            )
        return False


class PairExtractor: # Original class
    """Extracts complete key-value pairs from objects using stateless operations."""

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with columnar validation."""
        if not isinstance(obj, dict):
            return {}
        return {
            key: value
            for key, value in obj.items()
            if MessageValidator.is_valid_key(key) and MessageValidator.is_valid_value(value)
        }


class ValueParser:
    """Stateless utility for parsing values in columnar format."""

    @staticmethod
    def parse_value(value_str: str) -> Any:
        """Parse string value to the appropriate Python type."""
        if not value_str:
            return None
        cleaned_value = value_str.rstrip(',}').strip()
        if ValueParser._is_quoted_string(cleaned_value):
            return cleaned_value[1:-1]
        if cleaned_value.lower() == 'true':
            return True
        if cleaned_value.lower() == 'false':
            return False
        if cleaned_value.lower() == 'null':
            return None
        parsed_number = ValueParser._try_parse_number(cleaned_value)
        if parsed_number is not None:
            return parsed_number
        return cleaned_value

    @staticmethod
    def _is_quoted_string(value: str) -> bool:
        """Check if the value is a quoted string."""
        return len(value) >= 2 and value.startswith('"') and value.endswith('"')

    @staticmethod
    def _try_parse_number(value: str) -> Optional[Union[int, float]]:
        """Try to parse value as number."""
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return None


class MessageExtractor:
    """Stateless utility for extracting complete JSON messages."""

    @staticmethod
    def extract_messages(text: str) -> List[ParsedMessage]:
        """Extract complete JSON messages from text data."""
        if not text:
            return []
        extractor = MessageExtractionState()
        for ch in text:
            extractor.process_character(ch)
        extractor.finalize()
        return extractor.get_messages()

    @staticmethod
    def _update_braces(ch: str, count: int) -> int:
        """Update brace count based on character."""
        if ch == '{':
            return count + 1
        if ch == '}':
            return count - 1
        return count


class MessageExtractionState:
    """Handles message extraction state for MessageExtractor."""
    def __init__(self):
        self.messages: List[ParsedMessage] = []
        self.current_chars: List[str] = []
        self.brace_count: int = 0
        self.in_string: bool = False
        self.escape_next: bool = False

    def process_character(self, ch: str) -> None:
        """Process a single character."""
        self.current_chars.append(ch)
        if self.escape_next:
            self.escape_next = False
            return
        if ch == '\\':
            self.escape_next = True
            return
        if self._is_string_delimiter(ch):
            return
        if self.in_string:
            return
        self._handle_brace_character(ch)

    def _is_string_delimiter(self, ch: str) -> bool:
        """Handle string delimiter character."""
        if ch == '"' and not self.escape_next:
            self.in_string = not self.in_string
            return True
        return False

    def _handle_brace_character(self, ch: str) -> None:
        """Handle brace characters for message parsing."""
        self.brace_count = MessageExtractor._update_braces(ch, self.brace_count)
        if self.brace_count == 0 and len(self.current_chars) > 1:
            self._complete_message()

    def _complete_message(self) -> None:
        """Complete the current message."""
        content = ''.join(self.current_chars).strip()
        if content:
            self.messages.append(ParsedMessage(content=content, is_complete=True, brace_count=0))
        self.current_chars.clear()

    def finalize(self) -> None:
        """Finalize extraction and handle remaining incomplete message."""
        if self.current_chars:
            content = ''.join(self.current_chars).strip()
            if content:
                self.messages.append(ParsedMessage(
                    content=content, is_complete=self.brace_count == 0, brace_count=self.brace_count
                ))

    def get_messages(self) -> List[ParsedMessage]:
        """Get the list of extracted messages."""
        return self.messages


class MessageFormatter:
    """Stateless utility for message formatting."""
    @staticmethod
    def correct_format(message: str) -> Optional[str]:
        """Correct incomplete JSON format."""
        if not message or '{' not in message:
            return None
        open_braces = message.count('{')
        close_braces = message.count('}')
        if open_braces > close_braces:
            return message + '}' * (open_braces - close_braces)
        elif open_braces == close_braces and open_braces > 0:
            return message
        return None


class FieldExtractor:
    """Stateless utility for field extraction from malformed JSON."""
    @staticmethod
    def extract_fields(message: str) -> Dict[str, Any]:
        """Extract key-value pairs from malformed JSON."""
        if not message:
            return {}
        result = {}
        lines = message.split('\n')
        for line in lines:
            key_value = FieldExtractor._extract_key_value_from_line(line.strip())
            if key_value:
                key, value = key_value
                result[key] = value
        return result

    @staticmethod
    def _extract_key_value_from_line(line: str) -> Optional[tuple]:
        """Extract a key-value pair from a single line."""
        if not line or ':' not in line or '"' not in line:
            return None
        try:
            colon_pos = line.find(':')
            if colon_pos <= 0:
                return None
            key_part = line[:colon_pos].strip()
            value_part = line[colon_pos + 1:].strip()
            if not (key_part.startswith('"') and key_part.endswith('"')):
                return None
            key = key_part[1:-1]
            value = ValueParser.parse_value(value_part)
            return (key, value) if value is not None else None
        except (IndexError, AttributeError):
            return None


class JsonMessageDecoder:
    """Decoder for complete JSON messages."""
    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()

    def decode(self, message: ParsedMessage) -> Dict[str, Any]:
        """Decode complete JSON message."""
        try:
            obj = json.loads(message.content)
            if isinstance(obj, dict):
                return self._pair_extractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass
        return {}


class PartialMessageDecoder:
    """Decoder for partial/malformed JSON messages."""
    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()

    def decode(self, message: ParsedMessage) -> Dict[str, Any]:
        """Decode partial JSON message."""
        corrected = MessageFormatter.correct_format(message.content)
        if corrected:
            try:
                obj = json.loads(corrected)
                if isinstance(obj, dict):
                    return self._pair_extractor.extract_complete_pairs(obj)
            except json.JSONDecodeError:
                pass
        return FieldExtractor.extract_fields(message.content)


class ParquetStyleProcessor:
    """Main processor using Parquet-inspired columnar processing with dependency injection."""
    def __init__(self,
                 message_extractor: MessageExtractor = None,
                 json_decoder: JsonMessageDecoder = None,
                 partial_decoder: PartialMessageDecoder = None):
        self._message_extractor = message_extractor or MessageExtractor()
        self._json_decoder = json_decoder or JsonMessageDecoder()
        self._partial_decoder = partial_decoder or PartialMessageDecoder()

    def process_buffer(self, buffer: str) -> Dict[str, Any]: # Original took str
        """Process buffer using columnar approach."""
        # This method is part of the original structure and is no longer directly
        # called by the refactored StreamingJsonParser.
        messages = self._message_extractor.extract_messages(buffer)
        parsed_data = {}
        for message in messages:
            decoded_data = self._decode_message(message)
            parsed_data.update(decoded_data)
        return parsed_data

    def _decode_message(self, message: ParsedMessage) -> Dict[str, Any]:
        """Decode a single message using the appropriate decoder."""
        if message.is_complete:
            return self._json_decoder.decode(message)
        return self._partial_decoder.decode(message)

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
