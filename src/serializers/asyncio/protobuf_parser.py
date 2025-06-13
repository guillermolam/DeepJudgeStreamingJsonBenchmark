"""
Protocol Buffers streaming parser implementation.
Note: Protobuf is for binary serialization, so this implements JSON parsing
with Protobuf-inspired message framing and incremental decoding.
"""
import json
import struct
from typing import Any, Dict, Optional, List


class StreamingJsonParser:
    """Streaming JSON parser with Protocol Buffers-inspired message framing."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.message_buffer = bytearray()
        self.current_message_length = None
        self.bytes_read = 0

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using Protobuf-style framing.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer

        # Convert to bytes for Protobuf-style processing
        buffer_bytes = buffer.encode('utf-8')
        self.message_buffer.extend(buffer_bytes)

        self._parse_protobuf_style()

    def _parse_protobuf_style(self) -> None:
        """Parse using Protobuf-inspired message framing."""
        # Process complete messages from buffer
        while len(self.message_buffer) > 0:
            # Try to extract length-prefixed messages (Protobuf style)
            if self.current_message_length is None:
                if len(self.message_buffer) >= 4:
                    # Read message length (4 bytes, big-endian)
                    try:
                        self.current_message_length = struct.unpack('>I', self.message_buffer[:4])[0]
                        self.message_buffer = self.message_buffer[4:]
                    except struct.error:
                        # Fallback to JSON-based parsing
                        self._parse_json_messages()
                        break
                else:
                    break

            # Read message of specified length
            if self.current_message_length is not None:
                if len(self.message_buffer) >= self.current_message_length:
                    message_bytes = self.message_buffer[:self.current_message_length]
                    self.message_buffer = self.message_buffer[self.current_message_length:]

                    # Process message
                    self._process_message(message_bytes)
                    self.current_message_length = None
                else:
                    break

    def _parse_json_messages(self) -> None:
        """Fallback to JSON-based message parsing."""
        try:
            # Convert buffer back to string
            buffer_str = self.message_buffer.decode('utf-8', errors='ignore')
            self.message_buffer.clear()

            # Look for complete JSON objects
            self._extract_json_objects(buffer_str)

        except Exception:
            pass

    def _process_message(self, message_bytes: bytearray) -> None:
        """Process a complete message."""
        try:
            # Try to decode as JSON
            message_str = message_bytes.decode('utf-8')
            obj = json.loads(message_str)

            if isinstance(obj, dict):
                complete_pairs = self._extract_complete_pairs(obj)
                self.parsed_data.update(complete_pairs)

        except (UnicodeDecodeError, json.JSONDecodeError):
            # Try partial parsing
            self._try_partial_message_parse(message_bytes)

    def _try_partial_message_parse(self, message_bytes: bytearray) -> None:
        """Try to parse partial message."""
        try:
            # Decode with error handling
            message_str = message_bytes.decode('utf-8', errors='replace')

            # Look for JSON patterns
            if '{' in message_str:
                self._extract_json_objects(message_str)

        except Exception:
            pass

    def _extract_json_objects(self, text: str) -> None:
        """Extract JSON objects from text using Protobuf-style field parsing."""
        # Look for field-like patterns (Protobuf inspiration)
        current_obj = {}

        # Split by potential message boundaries
        segments = text.split('\n')

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            try:
                # Try direct JSON parsing
                obj = json.loads(segment)
                if isinstance(obj, dict):
                    complete_pairs = self._extract_complete_pairs(obj)
                    self.parsed_data.update(complete_pairs)

            except json.JSONDecodeError:
                # Try field-by-field parsing (Protobuf style)
                self._parse_protobuf_fields(segment)

    def _parse_protobuf_fields(self, segment: str) -> None:
        """Parse fields in Protobuf-inspired manner."""
        try:
            # Look for key-value patterns
            if ':' in segment and ('{' in segment or '"' in segment):
                # Try to extract partial JSON
                if '{' in segment:
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
                                complete_pairs = self._extract_complete_pairs(obj)
                                self.parsed_data.update(complete_pairs)
                        except json.JSONDecodeError:
                            pass

        except Exception:
            pass

    def _extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        complete_pairs = {}

        for key, value in obj.items():
            # Protobuf-style field validation
            if isinstance(key, str) and len(key) > 0:
                # Field numbers in Protobuf are always positive
                # Here we just ensure complete keys
                complete_pairs[key] = value

        return complete_pairs

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()
