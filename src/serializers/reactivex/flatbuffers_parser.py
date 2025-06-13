"""
FlatBuffers streaming parser implementation.
Note: FlatBuffers is for binary serialization with zero-copy access,
so this implements JSON parsing with FlatBuffers-inspired flat memory layout concepts.
"""
import json
from typing import Any, Dict, Optional, List


class StreamingJsonParser:
    """Streaming JSON parser with FlatBuffers-inspired flat memory layout."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.flat_buffer = []  # Flat representation of data
        self.offset_table = {}  # Offset table for quick access
        self.current_offset = 0

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using FlatBuffers-style layout.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer
        self._parse_flatbuffer_style()

    def _parse_flatbuffer_style(self) -> None:
        """Parse using FlatBuffers-inspired flat memory layout."""
        # FlatBuffers stores data in a flat binary format with offset tables
        # Here we simulate this with a flat list and offset tracking

        # Convert buffer to flat representation
        self._build_flat_representation()

        # Parse objects from flat representation
        self._parse_from_flat_buffer()

    def _build_flat_representation(self) -> None:
        """Build flat representation of the JSON data."""
        # Split buffer into tokens (FlatBuffers-style tokenization)
        tokens = self._tokenize_buffer()

        # Add tokens to flat buffer with offsets
        for token in tokens:
            self.flat_buffer.append(token)
            self.offset_table[self.current_offset] = len(self.flat_buffer) - 1
            self.current_offset += 1

    def _tokenize_buffer(self) -> List[str]:
        """Tokenize buffer into FlatBuffers-style tokens."""
        tokens = []
        current_token = ""
        in_string = False
        escape_next = False

        for char in self.buffer:
            if escape_next:
                current_token += char
                escape_next = False
                continue

            if char == '\\':
                current_token += char
                escape_next = True
                continue

            if char == '"':
                current_token += char
                if not escape_next:
                    in_string = not in_string
                continue

            if not in_string and char in '{}[],:\n\r\t ':
                if current_token.strip():
                    tokens.append(current_token.strip())
                    current_token = ""
                if char.strip():
                    tokens.append(char)
            else:
                current_token += char

        if current_token.strip():
            tokens.append(current_token.strip())

        return tokens

    def _parse_from_flat_buffer(self) -> None:
        """Parse JSON objects from flat buffer representation."""
        # Reconstruct JSON objects from flat tokens
        i = 0
        while i < len(self.flat_buffer):
            token = self.flat_buffer[i]

            if token == '{':
                # Start of object - parse using FlatBuffers-style offset jumping
                obj_end = self._find_object_end_flat(i)
                if obj_end > i:
                    obj_tokens = self.flat_buffer[i:obj_end + 1]
                    parsed_obj = self._reconstruct_object_from_tokens(obj_tokens)

                    if parsed_obj:
                        complete_pairs = self._extract_complete_pairs(parsed_obj)
                        self.parsed_data.update(complete_pairs)

                    i = obj_end + 1
                else:
                    i += 1
            else:
                i += 1

    def _find_object_end_flat(self, start_index: int) -> int:
        """Find end of object in flat buffer using FlatBuffers-style navigation."""
        brace_count = 0
        in_string = False

        for i in range(start_index, len(self.flat_buffer)):
            token = self.flat_buffer[i]

            if token == '"' and not in_string:
                in_string = True
                continue
            elif token == '"' and in_string:
                in_string = False
                continue

            if not in_string:
                if token == '{':
                    brace_count += 1
                elif token == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i

        return -1

    def _reconstruct_object_from_tokens(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Reconstruct JSON object from flat tokens."""
        try:
            # Join tokens back into JSON string
            json_str = ""
            for token in tokens:
                if token in '{}[],':
                    json_str += token
                elif token == ':':
                    json_str += ':'
                else:
                    # Add appropriate spacing
                    if json_str and json_str[-1] not in '{"[,:':
                        json_str += ' '
                    json_str += token

            # Clean up the JSON string
            json_str = self._clean_json_string(json_str)

            # Parse the reconstructed JSON
            obj = json.loads(json_str)
            return obj if isinstance(obj, dict) else None

        except (json.JSONDecodeError, ValueError):
            # Try partial reconstruction
            return self._try_partial_reconstruction(tokens)

    def _clean_json_string(self, json_str: str) -> str:
        """Clean up JSON string for parsing."""
        # Remove extra spaces and fix common issues
        import re

        # Fix spacing around colons and commas
        json_str = re.sub(r'\s*:\s*', ':', json_str)
        json_str = re.sub(r'\s*,\s*', ',', json_str)

        # Ensure proper spacing
        json_str = re.sub(r'([{,])\s*(["\w])', r'\1\2', json_str)
        json_str = re.sub(r'(["\w])\s*([,}])', r'\1\2', json_str)

        return json_str

    def _try_partial_reconstruction(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Try partial reconstruction of incomplete objects."""
        try:
            # Look for complete key-value pairs
            result = {}
            i = 1  # Skip opening brace

            while i < len(tokens) - 1:  # Skip closing brace
                # Look for key
                if tokens[i].startswith('"') and tokens[i].endswith('"'):
                    key = tokens[i][1:-1]  # Remove quotes

                    # Look for colon
                    if i + 1 < len(tokens) and tokens[i + 1] == ':':
                        # Look for value
                        if i + 2 < len(tokens):
                            value_token = tokens[i + 2]

                            # Parse value
                            try:
                                if value_token.startswith('"') and value_token.endswith('"'):
                                    value = value_token[1:-1]  # String value
                                elif value_token.lower() in ['true', 'false']:
                                    value = value_token.lower() == 'true'
                                elif value_token.lower() == 'null':
                                    value = None
                                else:
                                    value = json.loads(value_token)  # Number or other

                                result[key] = value
                                i += 3  # Move past key, colon, value

                                # Skip comma if present
                                if i < len(tokens) and tokens[i] == ',':
                                    i += 1

                            except (ValueError, json.JSONDecodeError):
                                i += 1
                        else:
                            break
                    else:
                        i += 1
                else:
                    i += 1

            return result if result else None

        except Exception:
            return None

    def _extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        complete_pairs = {}

        for key, value in obj.items():
            # FlatBuffers-style validation: ensure complete keys
            if isinstance(key, str) and len(key) > 0:
                # Partial string values are allowed per requirements
                complete_pairs[key] = value

        return complete_pairs

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()
