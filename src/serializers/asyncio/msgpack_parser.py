"""
MsgPack streaming parser implementation.
Note: MsgPack is binary format, so this implements JSON parsing
with MsgPack-inspired compact binary encoding and streaming concepts.
"""
import json
from typing import Any, Dict, Optional, Union, List


class StreamingJsonParser:
    """Streaming JSON parser with MsgPack-inspired compact binary encoding."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.binary_stream = bytearray()
        self.format_codes = {
            # MsgPack format codes (simplified)
            0x80: 'fixmap',  # 1000xxxx
            0x90: 'fixarray',  # 1001xxxx
            0xa0: 'fixstr',  # 101xxxxx
            0xc0: 'nil',  # 11000000
            0xc2: 'false',  # 11000010
            0xc3: 'true',  # 11000011
            0xca: 'float32',  # 11001010
            0xcb: 'float64',  # 11001011
            0xcc: 'uint8',  # 11001100
            0xcd: 'uint16',  # 11001101
            0xce: 'uint32',  # 11001110
            0xcf: 'uint64',  # 11001111
        }

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using MsgPack-style processing.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer

        # Convert to binary stream for MsgPack-style processing
        buffer_bytes = buffer.encode('utf-8')
        self.binary_stream.extend(buffer_bytes)

        self._parse_msgpack_style()

    def _parse_msgpack_style(self) -> None:
        """Parse using MsgPack-inspired compact encoding."""
        # MsgPack uses type-length-value encoding
        # Here we simulate this with JSON parsing

        # Convert binary stream back to text for JSON processing
        try:
            text_data = self.binary_stream.decode('utf-8', errors='ignore')

            # Process as MsgPack-style messages
            self._process_msgpack_messages(text_data)

        except Exception:
            pass

    def _process_msgpack_messages(self, text_data: str) -> None:
        """Process messages using MsgPack-inspired format detection."""
        # MsgPack messages are self-contained
        # Look for complete JSON objects as "messages"

        messages = self._extract_msgpack_messages(text_data)

        for message in messages:
            self._decode_msgpack_message(message)

    def _extract_msgpack_messages(self, text_data: str) -> List[str]:
        """Extract MsgPack-style messages from text data."""
        messages = []
        current_message = ""
        brace_count = 0
        in_string = False
        escape_next = False

        for char in text_data:
            current_message += char

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

                    if brace_count == 0 and current_message.strip():
                        # Complete message found
                        messages.append(current_message.strip())
                        current_message = ""

        # Handle incomplete message
        if current_message.strip() and brace_count > 0:
            messages.append(current_message.strip())

        return messages

    def _decode_msgpack_message(self, message: str) -> None:
        """Decode MsgPack-style message."""
        try:
            # Try direct JSON parsing first
            obj = json.loads(message)
            if isinstance(obj, dict):
                complete_pairs = self._extract_complete_pairs_msgpack(obj)
                self.parsed_data.update(complete_pairs)

        except json.JSONDecodeError:
            # Try MsgPack-style partial decoding
            self._decode_partial_msgpack(message)

    def _decode_partial_msgpack(self, message: str) -> None:
        """Decode partial MsgPack message."""
        try:
            # MsgPack-style format detection and correction
            if '{' in message:
                # Detect format type (map in MsgPack terms)
                corrected_message = self._correct_msgpack_format(message)

                if corrected_message:
                    try:
                        obj = json.loads(corrected_message)
                        if isinstance(obj, dict):
                            complete_pairs = self._extract_complete_pairs_msgpack(obj)
                            self.parsed_data.update(complete_pairs)
                    except json.JSONDecodeError:
                        # Try field-by-field extraction
                        self._extract_msgpack_fields(message)

        except Exception:
            pass

    def _correct_msgpack_format(self, message: str) -> Optional[str]:
        """Correct message format using MsgPack-inspired rules."""
        try:
            # MsgPack format correction: balance containers
            open_braces = message.count('{')
            close_braces = message.count('}')

            if open_braces > close_braces:
                # Add missing closing braces (MsgPack containers must be complete)
                corrected = message + '}' * (open_braces - close_braces)
                return corrected
            elif open_braces == close_braces and open_braces > 0:
                return message

            return None

        except Exception:
            return None

    def _extract_msgpack_fields(self, message: str) -> None:
        """Extract fields using MsgPack-style field parsing."""
        try:
            # MsgPack field extraction: look for key-value patterns
            result = {}

            # Simple field extraction
            lines = message.split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line and '"' in line:
                    # Try to extract key-value pair
                    try:
                        # Look for "key": value pattern
                        colon_pos = line.find(':')
                        if colon_pos > 0:
                            key_part = line[:colon_pos].strip()
                            value_part = line[colon_pos + 1:].strip()

                            # Extract key
                            if key_part.startswith('"') and key_part.endswith('"'):
                                key = key_part[1:-1]

                                # Extract value
                                value = self._parse_msgpack_value(value_part)
                                if value is not None:
                                    result[key] = value

                    except Exception:
                        continue

            if result:
                self.parsed_data.update(result)

        except Exception:
            pass

    def _parse_msgpack_value(self, value_str: str) -> Any:
        """Parse value using MsgPack-inspired type detection."""
        try:
            value_str = value_str.rstrip(',}')  # Remove trailing punctuation

            # MsgPack type detection
            if value_str.startswith('"') and value_str.endswith('"'):
                # String (fixstr in MsgPack)
                return value_str[1:-1]
            elif value_str.lower() == 'true':
                # Boolean true
                return True
            elif value_str.lower() == 'false':
                # Boolean false  
                return False
            elif value_str.lower() == 'null':
                # Nil
                return None
            elif value_str.isdigit():
                # Positive integer (uint in MsgPack)
                return int(value_str)
            elif value_str.startswith('-') and value_str[1:].isdigit():
                # Negative integer
                return int(value_str)
            elif '.' in value_str:
                # Float
                try:
                    return float(value_str)
                except ValueError:
                    return value_str
            else:
                # Default to string
                return value_str

        except Exception:
            return None

    def _extract_complete_pairs_msgpack(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with MsgPack-style validation."""
        complete_pairs = {}

        for key, value in obj.items():
            # MsgPack validation: keys must be strings
            if isinstance(key, str) and len(key) > 0:
                # MsgPack supports all JSON types
                if self._is_valid_msgpack_value(value):
                    complete_pairs[key] = value

        return complete_pairs

    def _is_valid_msgpack_value(self, value: Any) -> bool:
        """Check if value is valid for MsgPack encoding."""
        # MsgPack supports: nil, bool, int, float, str, bin, array, map, ext
        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(self._is_valid_msgpack_value(item) for item in value)
        if isinstance(value, dict):
            return all(isinstance(k, str) and self._is_valid_msgpack_value(v)
                       for k, v in value.items())

        return False

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()
