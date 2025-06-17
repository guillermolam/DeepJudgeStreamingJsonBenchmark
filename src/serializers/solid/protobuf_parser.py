"""
Protocol Buffers streaming parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by Protocol Buffers message framing.
The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original Protobuf-inspired helper classes remain but are no longer used by StreamingJsonParser.
"""
import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

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
    This version replaces the original Protobuf-style parser in this module.
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

# --- Original Protobuf-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class ParserState: # Original class
    """Immutable state container for the Protobuf parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


class FieldValidator:
    """Stateless validator for Protobuf-style fields."""

    @staticmethod
    def is_valid_protobuf_field(key: str) -> bool:
        """Validate if a key represents a valid Protobuf-style field."""
        return isinstance(key, str) and len(key) > 0

    @staticmethod
    def has_json_structure(segment: str) -> bool:
        """Check if segment contains JSON-like structure."""
        return ':' in segment and ('{' in segment or '"' in segment)


class PairExtractor:
    """Extracts complete key-value pairs from objects using stateless operations."""

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        if not isinstance(obj, dict):
            return {}

        return {
            key: value
            for key, value in obj.items()
            if FieldValidator.is_valid_protobuf_field(key)
        }


class MessageFrameParser:
    """Handles Protobuf-style message framing with stateless operations."""

    @staticmethod
    def try_parse_length_prefixed(message_buffer: bytearray) -> Optional[int]:
        """Try to parse a length-prefixed message."""
        if len(message_buffer) < 4:
            return None

        try:
            length = struct.unpack('>I', message_buffer[:4])[0]
            return length
        except struct.error:
            return None

    @staticmethod
    def extract_message(message_buffer: bytearray, length: int) -> Optional[bytearray]:
        """Extract a message of specified length."""
        total_length = length + 4  # +4 for length prefix
        if len(message_buffer) < total_length:
            return None

        message_bytes = message_buffer[4:total_length]
        del message_buffer[:total_length]
        return message_bytes


class JsonObjectExtractor:
    """Stateless utility for extracting JSON objects from text."""

    @staticmethod
    def extract_json_objects(text: str) -> Dict[str, Any]:
        """Extract JSON objects from text by processing segments."""
        result = {}
        segments = JsonObjectExtractor._split_into_segments(text)

        for segment in segments:
            segment_result = JsonObjectExtractor._process_single_segment(segment)
            if segment_result:
                result.update(segment_result)

        return result

    @staticmethod
    def _split_into_segments(text: str) -> List[str]:
        """Split text into processable segments."""
        return [segment.strip() for segment in text.split('\n') if segment.strip()]

    @staticmethod
    def _process_single_segment(segment: str) -> Dict[str, Any]:
        """Process a single text segment for JSON content."""
        direct_result = JsonObjectExtractor._try_direct_json_parse(segment)
        if direct_result:
            return direct_result
        return JsonObjectExtractor._try_field_parsing(segment)

    @staticmethod
    def _try_direct_json_parse(segment: str) -> Dict[str, Any]:
        """Attempt direct JSON parsing of segment."""
        try:
            obj = json.loads(segment)
            if isinstance(obj, dict):
                return PairExtractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass
        return {}

    @staticmethod
    def _try_field_parsing(segment: str) -> Dict[str, Any]:
        """Try field-by-field parsing for Protobuf-style segments."""
        if not FieldValidator.has_json_structure(segment):
            return {}
        if '{' in segment:
            return PartialJsonExtractor.extract_partial_json(segment)
        return {}


class PartialJsonExtractor:
    """Stateless utility for extracting partial JSON with brace balancing."""

    @staticmethod
    def extract_partial_json(segment: str) -> Dict[str, Any]:
        """Extract partial JSON from segment with automatic brace balancing."""
        start_pos = segment.find('{')
        if start_pos == -1:
            return {}
        json_part = segment[start_pos:]
        balanced_json = PartialJsonExtractor._balance_braces(json_part)
        return PartialJsonExtractor._parse_balanced_json(balanced_json)

    @staticmethod
    def _balance_braces(json_part: str) -> str:
        """Balance opening and closing braces in JSON string."""
        open_braces = json_part.count('{')
        close_braces = json_part.count('}')
        if open_braces > close_braces:
            return json_part + '}' * (open_braces - close_braces)
        return json_part

    @staticmethod
    def _parse_balanced_json(balanced_json: str) -> Dict[str, Any]:
        """Parse balanced JSON string."""
        try:
            obj = json.loads(balanced_json)
            if isinstance(obj, dict):
                return PairExtractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass
        return {}


class MessageDecoder:
    """Decodes individual messages with dependency injection."""

    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()

    def decode_message(self, message_bytes: bytearray) -> Dict[str, Any]:
        """Process a complete message with fallback mechanisms."""
        utf8_result = self._try_utf8_decode(message_bytes)
        if utf8_result:
            return utf8_result
        return self._try_partial_message_parse(message_bytes)

    def _try_utf8_decode(self, message_bytes: bytearray) -> Dict[str, Any]:
        """Try to decode message as UTF-8 JSON."""
        try:
            message_str = message_bytes.decode('utf-8')
            obj = json.loads(message_str)
            if isinstance(obj, dict):
                return self._pair_extractor.extract_complete_pairs(obj)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        return {}

    def _try_partial_message_parse(self, message_bytes: bytearray) -> Dict[str, Any]:
        """Try to parse a partial message with error recovery."""
        try:
            message_str = message_bytes.decode('utf-8', errors='replace')
            if '{' in message_str:
                return JsonObjectExtractor.extract_json_objects(message_str)
        except ValueError:
            pass
        return {}


class JsonFallbackParser:
    """Fallback JSON-based message parsing with dependency injection."""

    def __init__(self, message_decoder: MessageDecoder = None):
        self._message_decoder = message_decoder or MessageDecoder()

    def parse_json_messages(self, message_buffer: bytearray) -> Dict[str, Any]:
        """Fallback to JSON-based message parsing."""
        try:
            buffer_str = message_buffer.decode('utf-8', errors='ignore')
            message_buffer.clear()
            fake_message = buffer_str.encode('utf-8')
            return self._message_decoder.decode_message(bytearray(fake_message))
        except ValueError:
            return {}


class ProtobufStyleProcessor:
    """Main processor using Protobuf-inspired message framing with dependency injection."""

    def __init__(self,
                 frame_parser: MessageFrameParser = None,
                 message_decoder: MessageDecoder = None,
                 fallback_parser: JsonFallbackParser = None):
        self._frame_parser = frame_parser or MessageFrameParser()
        self._message_decoder = message_decoder or MessageDecoder()
        self._fallback_parser = fallback_parser or JsonFallbackParser(self._message_decoder)
        self._message_buffer = bytearray()

    def process_buffer(self, buffer: str) -> Dict[str, Any]: # Original took str
        """Parse using Protobuf-inspired message framing."""
        # This method is part of the original structure and is no longer directly
        # called by the refactored StreamingJsonParser.
        # If it were to be used, it would need adaptation for byte inputs.
        buffer_bytes = buffer.encode('utf-8') # Example adaptation
        self._message_buffer.extend(buffer_bytes)
        return self._parse_protobuf_style()

    def _parse_protobuf_style(self) -> Dict[str, Any]:
        """Parse using Protobuf-inspired message framing with clear separation."""
        parsed_data = {}
        while len(self._message_buffer) > 0:
            processing_result = self._process_next_message()
            if processing_result is None:
                fallback_data = self._try_fallback_parsing()
                if fallback_data:
                    parsed_data.update(fallback_data)
                break
            if processing_result:
                parsed_data.update(processing_result)
        return parsed_data

    def _process_next_message(self) -> Optional[Dict[str, Any]]:
        """Process the next complete message from buffer."""
        message_length = self._frame_parser.try_parse_length_prefixed(self._message_buffer)
        if message_length is None:
            return None
        message_bytes = self._frame_parser.extract_message(self._message_buffer, message_length)
        if message_bytes is None:
            return None
        return self._message_decoder.decode_message(message_bytes)

    def _try_fallback_parsing(self) -> Dict[str, Any]:
        """Try fallback parsing when length-prefixed parsing fails."""
        return self._fallback_parser.parse_json_messages(self._message_buffer)

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
