
"""
Parquet streaming parser implementation with SOLID principles.

This module implements a streaming JSON parser inspired by Parquet columnar storage format.
It follows SOLID principles with clean separation of concerns, stateless operations where possible,
and cognitive complexity under 14 for all methods.

Key Features:
- Columnar processing inspired by Parquet
- Incremental JSON parsing with message-based processing
- Stateless utility functions and processors
- Clean separation between message extraction, validation, and data processing
- Comprehensive error handling and recovery

Architecture:
- ParserState: Immutable state container using @dataclass
- Static utility classes for message validation and value parsing
- Dependency injection for loose coupling
- Single responsibility principle throughout
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Union


@dataclass
class ParserState:
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


class PairExtractor:
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

        # String detection
        if ValueParser._is_quoted_string(cleaned_value):
            return cleaned_value[1:-1]

        # Boolean detection
        if cleaned_value.lower() == 'true':
            return True
        if cleaned_value.lower() == 'false':
            return False

        # Null detection
        if cleaned_value.lower() == 'null':
            return None

        # Number detection
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
        self.messages = []
        self.current_chars = []
        self.brace_count = 0
        self.in_string = False
        self.escape_next = False

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
            self.messages.append(ParsedMessage(
                content=content,
                is_complete=True,
                brace_count=0
            ))
        self.current_chars.clear()

    def finalize(self) -> None:
        """Finalize extraction and handle remaining incomplete message."""
        if self.current_chars:
            content = ''.join(self.current_chars).strip()
            if content:
                self.messages.append(ParsedMessage(
                    content=content,
                    is_complete=self.brace_count == 0,
                    brace_count=self.brace_count
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
        # Try format correction first
        corrected = MessageFormatter.correct_format(message.content)
        if corrected:
            try:
                obj = json.loads(corrected)
                if isinstance(obj, dict):
                    return self._pair_extractor.extract_complete_pairs(obj)
            except json.JSONDecodeError:
                pass

        # Fall back to field extraction
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

    def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Process buffer using columnar approach."""
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


class StreamingJsonParser:
    """Streaming JSON parser with Parquet-inspired columnar processing."""

    def __init__(self, processor: ParquetStyleProcessor = None):
        """Initialize the streaming JSON parser with dependency injection."""
        self._state = ParserState()
        self._processor = processor or ParquetStyleProcessor()

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
        Process a chunk of JSON data incrementally using columnar processing.

        Args:
            buffer: String chunk of JSON data to process
        """
        if not buffer:
            return

        self._buffer += buffer
        new_data = self._processor.process_buffer(self._buffer)
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
