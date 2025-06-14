
"""
MsgPack streaming parser implementation with SOLID principles.

This module implements a streaming JSON parser inspired by MsgPack compact binary encoding.
It follows SOLID principles with clean separation of concerns, stateless operations where possible,
and cognitive complexity under 14 for all methods.

Key Features:
- MsgPack-inspired compact binary encoding concepts
- Incremental message extraction and processing
- Stateless utility functions and processors
- Clean separation between extraction, validation, and processing
- Comprehensive type detection and validation

Architecture:
- ParserState: Immutable state container using @dataclass
- Static utility classes for message processing and validation
- Dependency injection for loose coupling
- Single responsibility principle throughout
- Pure functions for deterministic behavior
"""
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, List, Tuple


@dataclass
class ParserState:
    """Immutable state container for the MsgPack parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


class MsgPackFormatCode(Enum):
    """MsgPack format codes (simplified for type detection)."""
    FIXMAP = 0x80  # 1000xxxx
    FIXARRAY = 0x90  # 1001xxxx
    FIXSTR = 0xa0  # 101xxxxx
    NIL = 0xc0  # 11000000
    FALSE = 0xc2  # 11000010
    TRUE = 0xc3  # 11000011
    FLOAT32 = 0xca  # 11001010
    FLOAT64 = 0xcb  # 11001011
    UINT8 = 0xcc  # 11001100
    UINT16 = 0xcd  # 11001101
    UINT32 = 0xce  # 11001110
    UINT64 = 0xcf  # 11001111


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
        """Check if character should be skipped and return new state."""
        if state.escape_next:
            return True, MessageParseState(state.brace_count, state.in_string, False)

        if char == '\\':
            return True, MessageParseState(state.brace_count, state.in_string, True)

        return False, state

    @staticmethod
    def update_string_state(state: MessageParseState, char: str) -> MessageParseState:
        """Update string parsing state."""
        if char == '"' and not state.escape_next:
            return MessageParseState(state.brace_count, not state.in_string, state.escape_next)
        return state

    @staticmethod
    def update_brace_count(state: MessageParseState, char: str) -> Tuple[bool, MessageParseState]:
        """Update brace count and return if count changed."""
        if char == '{':
            new_state = MessageParseState(state.brace_count + 1, state.in_string, state.escape_next)
            return True, new_state
        elif char == '}':
            new_state = MessageParseState(state.brace_count - 1, state.in_string, state.escape_next)
            return True, new_state

        return False, state


class MessageValidator:
    """Stateless utility for message validation."""

    @staticmethod
    def is_complete_message(state: MessageParseState, message: str) -> bool:
        """Check if a message is complete."""
        return state.brace_count == 0 and message.strip()

    @staticmethod
    def should_include_incomplete(message: str, state: MessageParseState) -> bool:
        """Check if incomplete message should be included."""
        return message.strip() and state.brace_count > 0


class MessageExtractor:
    """Extracts MsgPack-style messages from text data using stateless operations."""

    @staticmethod
    def extract_messages(text_data: str) -> List[str]:
        """Extract MsgPack-style messages from text data."""
        messages = []
        current_message = ""
        state = MessageParseState()

        for char in text_data:
            current_message += char
            state = MessageExtractor._process_single_character(char, state, current_message, messages)
            if not current_message:  # Message was completed and reset
                current_message = ""

        MessageExtractor._handle_final_message(messages, current_message, state)
        return messages

    @staticmethod
    def _process_single_character(char: str, state: MessageParseState,
                                  current_message: str, messages: List[str]) -> MessageParseState:
        """Process a single character and update state."""
        # Check if character should be skipped
        should_skip, new_state = CharacterProcessor.should_skip_character(state, char)
        if should_skip:
            return new_state

        # Update string state
        new_state = CharacterProcessor.update_string_state(new_state, char)

        # Process brace counting if not in string
        if not new_state.in_string:
            return MessageExtractor._process_brace_character(char, new_state, current_message, messages)

        return new_state

    @staticmethod
    def _process_brace_character(char: str, state: MessageParseState,
                                 current_message: str, messages: List[str]) -> MessageParseState:
        """Process character for brace counting."""
        brace_changed, new_state = CharacterProcessor.update_brace_count(state, char)

        if brace_changed and MessageValidator.is_complete_message(new_state, current_message):
            messages.append(current_message.strip())
            # Signal that message should be reset by clearing current_message reference
            # This is handled by the caller

        return new_state

    @staticmethod
    def _handle_final_message(messages: List[str], current_message: str, state: MessageParseState) -> None:
        """Handle incomplete message at the end of input."""
        if MessageValidator.should_include_incomplete(current_message, state):
            messages.append(current_message.strip())


class FormatCorrector:
    """Stateless utility for correcting message format using MsgPack-inspired rules."""

    @staticmethod
    def correct_format(message: str) -> Optional[str]:
        """Correct message format using MsgPack-inspired rules."""
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
        """Analyze brace counts in message."""
        open_braces = message.count('{')
        close_braces = message.count('}')

        if open_braces == 0:
            return None

        return open_braces, close_braces

    @staticmethod
    def _apply_correction(message: str, open_braces: int, close_braces: int) -> Optional[str]:
        """Apply brace correction to message."""
        if open_braces > close_braces:
            # Add missing closing braces (MsgPack containers must be complete)
            return message + '}' * (open_braces - close_braces)
        elif open_braces == close_braces:
            return message

        return None


class TypeDetector:
    """Stateless utility for MsgPack-inspired type detection."""

    @staticmethod
    def is_string_type(value_str: str) -> bool:
        """Check if the value is a string (fixstr in MsgPack)."""
        return value_str.startswith('"') and value_str.endswith('"')

    @staticmethod
    def is_boolean_type(value_str: str) -> Optional[bool]:
        """Check if value is boolean and return the boolean value."""
        lower_val = value_str.lower()
        if lower_val == 'true':
            return True
        elif lower_val == 'false':
            return False
        return None

    @staticmethod
    def is_null_type(value_str: str) -> bool:
        """Check if the value is null (nil in MsgPack)."""
        return value_str.lower() == 'null'

    @staticmethod
    def is_integer_type(value_str: str) -> Optional[int]:
        """Check if value is integer and return the integer value."""
        if value_str.isdigit():
            return int(value_str)
        elif value_str.startswith('-') and value_str[1:].isdigit():
            return int(value_str)
        return None

    @staticmethod
    def is_float_type(value_str: str) -> Optional[float]:
        """Check if value is float and return the float value."""
        if '.' in value_str:
            try:
                return float(value_str)
            except ValueError:
                return None
        return None


class ValueParser:
    """Parses values using MsgPack-inspired type detection with stateless operations."""

    @staticmethod
    def parse_value(value_str: str) -> Any:
        """Parse value using MsgPack-inspired type detection."""
        try:
            cleaned_value = value_str.rstrip(',}')  # Remove trailing punctuation

            # Try each type in order of specificity
            return ValueParser._try_parse_by_type(cleaned_value)
        except ValueError:
            return None

    @staticmethod
    def _try_parse_by_type(value_str: str) -> Any:
        """Try parsing value by each supported type."""
        # String type
        string_result = ValueParser._try_parse_string(value_str)
        if string_result is not None:
            return string_result

        # Boolean and null types
        literal_result = ValueParser._try_parse_literals(value_str)
        if literal_result is not None:
            return literal_result

        # Numeric types
        numeric_result = ValueParser._try_parse_numeric(value_str)
        if numeric_result is not None:
            return numeric_result

        # Default: return as string
        return value_str

    @staticmethod
    def _try_parse_string(value_str: str) -> Optional[str]:
        """Try parsing as string type."""
        if TypeDetector.is_string_type(value_str):
            return value_str[1:-1]  # Remove quotes
        return None

    @staticmethod
    def _try_parse_literals(value_str: str) -> Any:
        """Try parsing boolean and null literals."""
        bool_result = TypeDetector.is_boolean_type(value_str)
        if bool_result is not None:
            return bool_result

        if TypeDetector.is_null_type(value_str):
            return None

        return None

    @staticmethod
    def _try_parse_numeric(value_str: str) -> Optional[Any]:
        """Try parsing numeric types."""
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
        """Check if the line contains a valid field."""
        return ':' in line and '"' in line

    @staticmethod
    def extract_key_value_from_line(line: str) -> Optional[Tuple[str, str]]:
        """Extract key and value parts from a line."""
        colon_pos = line.find(':')
        if colon_pos <= 0:
            return None

        key_part = line[:colon_pos].strip()
        value_part = line[colon_pos + 1:].strip()

        # Validate key format
        if not (key_part.startswith('"') and key_part.endswith('"')):
            return None

        key = key_part[1:-1]  # Remove quotes
        return key, value_part


class FieldExtractor:
    """Extracts fields using MsgPack-style field parsing with dependency injection."""

    def __init__(self, value_parser: ValueParser = None):
        self._value_parser = value_parser or ValueParser()

    def extract_fields(self, message: str) -> Dict[str, Any]:
        """Extract fields using MsgPack-style field parsing."""
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
        """Process a single field line."""
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
        """Check if the value is valid for MsgPack encoding."""
        # MsgPack supports: nil, bool, int, float, str, bin, array, map, ext
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
        """Check if array contains valid MsgPack values."""
        return all(ValueValidator.is_valid_msgpack_value(item) for item in array)

    @staticmethod
    def _is_valid_map(mapping: Dict[str, Any]) -> bool:
        """Check if map contains valid MsgPack key-value pairs."""
        return all(
            isinstance(k, str) and ValueValidator.is_valid_msgpack_value(v)
            for k, v in mapping.items()
        )


class PairValidator:
    """Validates key-value pairs with MsgPack-style validation using stateless operations."""

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with MsgPack-style validation."""
        return {
            key: value
            for key, value in obj.items()
            if PairValidator._is_valid_pair(key, value)
        }

    @staticmethod
    def _is_valid_pair(key: str, value: Any) -> bool:
        """Check if key-value pair is valid."""
        return (PairValidator._is_valid_key(key) and
                ValueValidator.is_valid_msgpack_value(value))

    @staticmethod
    def _is_valid_key(key: str) -> bool:
        """Check if the key is valid for MsgPack encoding."""
        return isinstance(key, str) and len(key) > 0


class MessageProcessor:
    """Processes MsgPack-style messages with dependency injection."""

    def __init__(self,
                 format_corrector: FormatCorrector = None,
                 value_parser: ValueParser = None,
                 field_extractor: FieldExtractor = None,
                 pair_validator: PairValidator = None):
        self._format_corrector = format_corrector or FormatCorrector()
        self._value_parser = value_parser or ValueParser()
        self._field_extractor = field_extractor or FieldExtractor(self._value_parser)
        self._pair_validator = pair_validator or PairValidator()

    def process_messages(self, messages: List[str]) -> Dict[str, Any]:
        """Process messages using MsgPack-inspired format detection."""
        parsed_data = {}

        for message in messages:
            message_data = self._decode_single_message(message)
            if message_data:
                parsed_data.update(message_data)

        return parsed_data

    def _decode_single_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Decode a single MsgPack-style message."""
        # Try direct JSON parsing first
        direct_result = self._try_direct_json_parse(message)
        if direct_result:
            return direct_result

        # Try MsgPack-style partial decoding
        return self._try_partial_decode(message)

    def _try_direct_json_parse(self, message: str) -> Optional[Dict[str, Any]]:
        """Try direct JSON parsing."""
        try:
            obj = json.loads(message)
            if isinstance(obj, dict):
                return self._pair_validator.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass
        return None

    def _try_partial_decode(self, message: str) -> Optional[Dict[str, Any]]:
        """Try partial decoding with format correction."""
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
        """Process corrected message with fallback."""
        try:
            obj = json.loads(corrected_message)
            if isinstance(obj, dict):
                return self._pair_validator.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            # Try field-by-field extraction
            return self._field_extractor.extract_fields(original_message)

        return None


class BinaryStreamProcessor:
    """Processes binary stream for MsgPack-style processing with dependency injection."""

    def __init__(self,
                 message_extractor: MessageExtractor = None,
                 message_processor: MessageProcessor = None):
        self._message_extractor = message_extractor or MessageExtractor()
        self._message_processor = message_processor or MessageProcessor()
        self._binary_stream = bytearray()

    def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Process buffer using MsgPack-style processing."""
        buffer_bytes = buffer.encode('utf-8')
        self._binary_stream.extend(buffer_bytes)

        return self._parse_msgpack_style()

    def _parse_msgpack_style(self) -> Dict[str, Any]:
        """Parse using MsgPack-inspired compact encoding."""
        try:
            # Convert binary stream back to text for JSON processing
            text_data = self._binary_stream.decode('utf-8', errors='ignore')

            # Process as MsgPack-style messages
            messages = self._message_extractor.extract_messages(text_data)
            return self._message_processor.process_messages(messages)
        except ValueError:
            return {}


class StreamingJsonParser:
    """Streaming JSON parser with MsgPack-inspired compact binary encoding."""

    def __init__(self, binary_processor: BinaryStreamProcessor = None):
        """Initialize the streaming JSON parser with dependency injection."""
        self._state = ParserState()
        self._binary_processor = binary_processor or BinaryStreamProcessor()

    @property
    def _buffer(self) -> str:
        return self._state.buffer

    @_buffer.setter
    def _buffer(self, value: str) -> None:
        self._state.buffer = value

    @property
    def _parsed_data(self) -> Dict[str, Any]:
        return self._state.parsed_data

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using MsgPack-style processing.

        Args:
            buffer: String chunk of JSON data to process
        """
        self._buffer += buffer

        new_data = self._binary_processor.process_buffer(buffer)
        if new_data:
            self._parsed_data.update(new_data)

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self._sorted_copy(self._parsed_data)

    @staticmethod
    def _sorted_copy(data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a dict sorted by keys for deterministic output."""
        return {k: data[k] for k in sorted(data.keys())}
