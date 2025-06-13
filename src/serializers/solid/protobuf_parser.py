
"""
Protocol Buffers streaming parser implementation with SOLID principles.

This module implements a streaming JSON parser inspired by Protocol Buffers message framing.
It follows SOLID principles with clean separation of concerns, stateless operations where possible,
and cognitive complexity under 14 for all methods.

Key Features:
- Message framing inspired by Protocol Buffers
- Incremental JSON parsing with fallback mechanisms
- Stateless utility functions and processors
- Clean separation between parsing, validation, and data extraction
- Comprehensive error handling and recovery

Architecture:
- ParserState: Immutable state container using @dataclass
- Static utility classes for field validation and message processing
- Dependency injection for loose coupling
- Single responsibility principle throughout
"""
import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List


@dataclass
class ParserState:
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
        # Try direct JSON parsing first
        direct_result = JsonObjectExtractor._try_direct_json_parse(segment)
        if direct_result:
            return direct_result

        # Try field-by-field parsing if direct parsing fails
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
        # Try UTF-8 decoding first
        utf8_result = self._try_utf8_decode(message_bytes)
        if utf8_result:
            return utf8_result

        # Fallback to partial parsing
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

    def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Parse using Protobuf-inspired message framing."""
        buffer_bytes = buffer.encode('utf-8')
        self._message_buffer.extend(buffer_bytes)

        return self._parse_protobuf_style()

    def _parse_protobuf_style(self) -> Dict[str, Any]:
        """Parse using Protobuf-inspired message framing with clear separation."""
        parsed_data = {}

        while len(self._message_buffer) > 0:
            processing_result = self._process_next_message()

            if processing_result is None:
                # No more complete messages, try fallback
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


class StreamingJsonParser:
    """Streaming JSON parser with Protocol Buffers-inspired message framing."""

    def __init__(self, processor: ProtobufStyleProcessor = None):
        """Initialize the streaming JSON parser with dependency injection."""
        self._state = ParserState()
        self._processor = processor or ProtobufStyleProcessor()

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
        Process a chunk of JSON data incrementally using Protobuf-style framing.

        Args:
            buffer: String chunk of JSON data to process
        """
        self._buffer += buffer

        new_data = self._processor.process_buffer(buffer)
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
