"""
Parquet streaming parser implementation.
Note: Parquet is columnar storage format, so this implements JSON parsing
with Parquet-inspired columnar processing and metadata handling.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MessagePackType(Enum):
    """MsgPack type constants for better readability."""
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
class _ScanState:
    """Internal state holder for message extraction."""
    current: list[str]  # incremental chars of the current JSON snippet
    brace_count: int  # open–close brace balance
    in_string: bool  # inside a '"' string?
    escape_next: bool  # the previous char was a backslash?


@dataclass(frozen=True)
class ParsedMessage:
    """Immutable data_gen structure for parsed messages."""
    content: str
    is_complete: bool
    brace_count: int


class MessageExtractor:
    """Pure functions for message extraction with improved readability."""

    @staticmethod
    def extract_messages(text: str) -> List[ParsedMessage]:
        """Extract complete JSON messages from text data_gen."""
        if not text:
            return []

        state = _ScanState(current=[], brace_count=0, in_string=False, escape_next=False)
        messages: List[ParsedMessage] = []

        for ch in text:
            MessageExtractor._consume_char(ch, state, messages)

        # Push the trailing incomplete chunk (if any)
        trailing = MessageExtractor._flush(state)
        if trailing:
            messages.append(trailing)

        return messages

    @staticmethod
    def _consume_char(
            ch: str,
            st: _ScanState,
            out: List[ParsedMessage]
    ) -> None:
        """Process a single character and update state."""
        st.current.append(ch)

        if st.escape_next:  # the previous char was '\'
            st.escape_next = False
            return

        if ch == '\\':  # start of an escape
            st.escape_next = True
            return

        if ch == '"' and not st.escape_next:  # toggle string mode
            st.in_string = not st.in_string
            return

        if st.in_string:  # ignore everything inside strings
            return

        st.brace_count = MessageExtractor._update_braces(ch, st.brace_count)
        if st.brace_count == 0:
            complete = MessageExtractor._flush(st, is_complete=True)
            if complete:
                out.append(complete)

    @staticmethod
    def _update_braces(ch: str, count: int) -> int:
        """Pure function to update brace count."""
        if ch == '{':
            return count + 1
        if ch == '}':
            return count - 1
        return count

    @staticmethod
    def _flush(st: _ScanState, is_complete: bool = False) -> Optional[ParsedMessage]:
        """Return a ParsedMessage if there is anything buffered, then reset buffer."""
        if not st.current:
            return None

        content = ''.join(st.current).strip()
        st.current.clear()  # reset for the next fragment
        return ParsedMessage(
            content=content,
            is_complete=is_complete or st.brace_count == 0,
            brace_count=st.brace_count
        )


class ValueParser:
    """Pure functions for value parsing."""

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


class MessageValidator:
    """Pure functions for message validation."""

    @staticmethod
    def is_valid_value(value: Any) -> bool:
        """Check if the value is valid for MsgPack encoding."""
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

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only complete and valid key-value pairs."""
        if not isinstance(obj, dict):
            return {}

        return {
            key: value
            for key, value in obj.items()
            if isinstance(key, str) and len(key) > 0 and MessageValidator.is_valid_value(value)
        }


class MessageFormatter:
    """Pure functions for message formatting."""

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
    """Pure functions for field extraction."""

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
    def _extract_key_value_from_line(line: str) -> Optional[tuple[str, Any]]:
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

        except (IndexError, AttributeError):  # More specific exceptions
            return None


class IMessageDecoder(ABC):
    """Interface for message decoders (Interface Segregation Principle)."""

    @abstractmethod
    def decode(self, message: ParsedMessage) -> Dict[str, Any]:
        """Decode a message to key-value pairs."""
        pass


class JsonMessageDecoder(IMessageDecoder):
    """Decoder for complete JSON messages."""

    def decode(self, message: ParsedMessage) -> Dict[str, Any]:
        """Decode complete JSON message."""
        try:
            obj = json.loads(message.content)
            if isinstance(obj, dict):
                return MessageValidator.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass

        return {}


class PartialMessageDecoder(IMessageDecoder):
    """Decoder for partial/malformed JSON messages."""

    def decode(self, message: ParsedMessage) -> Dict[str, Any]:
        """Decode partial JSON message."""
        # Try format correction first
        corrected = MessageFormatter.correct_format(message.content)
        if corrected:
            try:
                obj = json.loads(corrected)
                if isinstance(obj, dict):
                    return MessageValidator.extract_complete_pairs(obj)
            except json.JSONDecodeError:
                pass

        # Fall back to field extraction
        return FieldExtractor.extract_fields(message.content)


class MessageDecoderFactory:
    """Factory for creating appropriate decoders (Factory Pattern)."""

    @staticmethod
    def create_decoder(message: ParsedMessage) -> IMessageDecoder:
        """Create the appropriate decoder based on message completeness."""
        if message.is_complete:
            return JsonMessageDecoder()
        return PartialMessageDecoder()


class StreamingJsonParser:
    """
    Streaming JSON parser with MsgPack-inspired compact binary encoding.

    This class follows SOLID principles:
    - Single Responsibility: Only handles the main parsing workflow
    - Open/Closed: Extensible through decoder interfaces
    - Liskov Substitution: Decoders are interchangeable
    - Interface Segregation: Separate interfaces for different concerns
    - Dependency Inversion: Depends on abstractions, not concretions
    """

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._buffer = ""
        self._parsed_data = {}
        self._binary_stream = bytearray()

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data_gen incrementally.

        Args:
            buffer: String chunk of JSON data_gen to process
        """
        if not buffer:
            return

        self._buffer += buffer
        self._update_binary_stream(buffer)
        self._process_messages()

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self._parsed_data.copy()

    def _update_binary_stream(self, buffer: str) -> None:
        """Update binary stream with new buffer data_gen."""
        buffer_bytes = buffer.encode('utf-8')
        self._binary_stream.extend(buffer_bytes)

    def _process_messages(self) -> None:
        """Process all messages in the current buffer."""
        try:
            text_data = self._binary_stream.decode('utf-8', errors='ignore')
            messages = MessageExtractor.extract_messages(text_data)

            for message in messages:
                decoded_data = self._decode_message(message)
                self._parsed_data.update(decoded_data)

        except (UnicodeDecodeError, AttributeError, TypeError):
            pass

    @staticmethod
    def _decode_message(message: ParsedMessage) -> Dict[str, Any]:
        """Decode a single message using the appropriate decoder."""
        decoder = MessageDecoderFactory.create_decoder(message)
        return decoder.decode(message)
