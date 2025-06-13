"""
Protocol Buffers streaming parser implementation.
Note: Protobuf is for binary serialization, so this implements JSON parsing
with Protobuf-inspired message framing and incremental decoding.
"""
import json
import struct
from typing import Any, Dict, Optional


class PairExtractor:
    """Extracts complete key-value pairs from objects."""

    def extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        complete_pairs = {}

        for key, value in obj.items():
            if self._is_valid_protobuf_field(key):
                complete_pairs[key] = value

        return complete_pairs

    @staticmethod
    def _is_valid_protobuf_field(key: str) -> bool:
        """Protobuf-style field validation."""
        return isinstance(key, str) and len(key) > 0


class MessageFrameParser:
    """Handles Protobuf-style message framing."""

    def __init__(self):
        self._current_message_length = None

    @staticmethod
    def try_parse_length_prefixed(message_buffer: bytearray) -> Optional[int]:
        """Try to parse a length-prefixed message."""
        if len(message_buffer) >= 4:
            try:
                length = struct.unpack('>I', message_buffer[:4])[0]
                return length
            except struct.error:
                return None
        return None

    @staticmethod
    def extract_message(message_buffer: bytearray, length: int) -> Optional[bytearray]:
        """Extract a message of specified length."""
        if len(message_buffer) >= length + 4:  # +4 for length prefix
            message_bytes = message_buffer[4:4 + length]
            # Remove processed bytes
            del message_buffer[:4 + length]
            return message_bytes
        return None


class MessageDecoder:
    """Decodes individual messages."""

    def __init__(self, pair_extractor: PairExtractor):
        self._pair_extractor = pair_extractor

    def decode_message(self, message_bytes: bytearray) -> Dict[str, Any]:
        """Process a complete message."""
        try:
            # Try to decode as JSON
            message_str = message_bytes.decode('utf-8')
            obj = json.loads(message_str)

            if isinstance(obj, dict):
                return self._pair_extractor.extract_complete_pairs(obj)

        except (UnicodeDecodeError, json.JSONDecodeError):
            # Try partial parsing
            return self._try_partial_message_parse(message_bytes)

        return {}

    def _try_partial_message_parse(self, message_bytes: bytearray) -> Dict[str, Any]:
        """Try to parse a partial message."""
        try:
            # Decode with error handling
            message_str = message_bytes.decode('utf-8', errors='replace')

            # Look for JSON patterns
            if '{' in message_str:
                return self._extract_json_objects(message_str)

        except ValueError:
            pass

        return {}

    def _extract_json_objects(self, text: str) -> Dict[str, Any]:
        """Extract JSON objects from text."""
        result = {}

        # Split by potential message boundaries
        segments = text.split('\n')

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            segment_result = self._process_segment(segment)
            if segment_result:
                result.update(segment_result)

        return result

    def _process_segment(self, segment: str) -> Dict[str, Any]:
        """Process a single segment."""
        try:
            # Try direct JSON parsing
            obj = json.loads(segment)
            if isinstance(obj, dict):
                return self._pair_extractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            # Try field-by-field parsing (Protobuf style)
            return self._parse_protobuf_fields(segment)

        return {}

    def _parse_protobuf_fields(self, segment: str) -> Dict[str, Any]:
        """Parse fields in a Protobuf-inspired manner."""
        try:
            # Look for key-value patterns
            if not (':' in segment and ('{' in segment or '"' in segment)):
                return {}

            # Try to extract partial JSON
            if '{' in segment:
                return self._extract_partial_json(segment)

        except ValueError:
            pass

        return {}

    def _extract_partial_json(self, segment: str) -> Dict[str, Any]:
        """Extract partial JSON from segment."""
        start_pos = segment.find('{')
        json_part = segment[start_pos:]

        # Balance braces
        open_braces = json_part.count('{')
        close_braces = json_part.count('}')

        if open_braces > close_braces:
            balanced_json = json_part + '}' * (open_braces - close_braces)

            try:
                obj = json.loads(balanced_json)
                if isinstance(obj, dict):
                    return self._pair_extractor.extract_complete_pairs(obj)
            except json.JSONDecodeError:
                pass

        return {}


class JsonFallbackParser:
    """Fallback JSON-based message parsing."""

    def __init__(self, message_decoder: MessageDecoder):
        self._message_decoder = message_decoder

    def parse_json_messages(self, message_buffer: bytearray) -> Dict[str, Any]:
        """Fallback to JSON-based message parsing."""
        try:
            # Convert buffer back to string
            buffer_str = message_buffer.decode('utf-8', errors='ignore')
            message_buffer.clear()

            # Create a fake message for processing
            fake_message = buffer_str.encode('utf-8')
            return self._message_decoder.decode_message(bytearray(fake_message))

        except ValueError:
            return {}


class ProtobufStyleProcessor:
    """Main processor using Protobuf-inspired message framing."""

    def __init__(self):
        self._pair_extractor = PairExtractor()
        self._frame_parser = MessageFrameParser()
        self._message_decoder = MessageDecoder(self._pair_extractor)
        self._fallback_parser = JsonFallbackParser(self._message_decoder)
        self._message_buffer = bytearray()

    def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Parse using Protobuf-inspired message framing."""
        # Convert to bytes for Protobuf-style processing
        buffer_bytes = buffer.encode('utf-8')
        self._message_buffer.extend(buffer_bytes)

        return self._parse_protobuf_style()

    def _parse_protobuf_style(self) -> Dict[str, Any]:
        """Parse using Protobuf-inspired message framing."""
        parsed_data = {}

        # Process complete messages from buffer
        while len(self._message_buffer) > 0:
            # Try to extract length-prefixed messages (Protobuf style)
            message_length = self._frame_parser.try_parse_length_prefixed(self._message_buffer)

            if message_length is None:
                # Fallback to JSON-based parsing
                fallback_data = self._fallback_parser.parse_json_messages(self._message_buffer)
                if fallback_data:
                    parsed_data.update(fallback_data)
                break

            # Extract a message of specified length
            message_bytes = self._frame_parser.extract_message(self._message_buffer, message_length)

            if message_bytes is None:
                break  # Not enough data_gen for a complete message

            # Process message
            message_data = self._message_decoder.decode_message(message_bytes)
            if message_data:
                parsed_data.update(message_data)

        return parsed_data


class StreamingJsonParser:
    """Streaming JSON parser with Protocol Buffers-inspired message framing."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._buffer = ""
        self._parsed_data = {}
        self._processor = ProtobufStyleProcessor()

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data_gen incrementally using Protobuf-style framing.

        Args:
            buffer: String chunk of JSON data_gen to process
        """
        self._buffer += buffer

        # Process using Protobuf-style message framing
        new_data = self._processor.process_buffer(buffer)
        if new_data:
            self._parsed_data.update(new_data)

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self._parsed_data.copy()
