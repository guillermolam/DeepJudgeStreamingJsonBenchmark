"""
CBOR (Concise Binary Object Representation) streaming parser implementation.
Note: CBOR is binary format, so this implements JSON parsing
with CBOR-inspired compact encoding and streaming concepts.
"""
import json
from typing import Any, Dict, Optional, Union, List


class StreamingJsonParser:
    """Streaming JSON parser with CBOR-inspired compact encoding and streaming."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.compact_buffer = []  # CBOR-style compact representation
        self.major_type_map = {
            0: 'unsigned_int',
            1: 'negative_int',
            2: 'byte_string',
            3: 'text_string',
            4: 'array',
            5: 'map',
            6: 'tag',
            7: 'float_simple'
        }

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using CBOR-style processing.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer
        self._parse_cbor_style()

    def _parse_cbor_style(self) -> None:
        """Parse using CBOR-inspired compact streaming."""
        # CBOR uses major types and compact encoding
        # Here we simulate this with compact JSON processing

        # Convert to CBOR-style compact tokens
        compact_tokens = self._tokenize_cbor_style()

        # Process tokens as CBOR-style data items
        self._process_cbor_tokens(compact_tokens)

    def _tokenize_cbor_style(self) -> List[Dict[str, Any]]:
        """Tokenize buffer into CBOR-style data items."""
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

                    # End of string - create CBOR-style token
                    if not in_string and current_token.startswith('"'):
                        tokens.append({
                            'major_type': 3,  # text string
                            'value': current_token[1:-1],  # Remove quotes
                            'raw': current_token
                        })
                        current_token = ""
                continue

            if not in_string:
                if char in '{}[],:\n\r\t ':
                    if current_token.strip():
                        # Determine CBOR major type
                        token_info = self._classify_cbor_token(current_token.strip())
                        tokens.append(token_info)
                        current_token = ""

                    if char.strip() and char in '{}[],':
                        # Structural tokens
                        tokens.append({
                            'major_type': 'structural',
                            'value': char,
                            'raw': char
                        })
                else:
                    current_token += char
            else:
                current_token += char

        if current_token.strip():
            token_info = self._classify_cbor_token(current_token.strip())
            tokens.append(token_info)

        return tokens

    def _classify_cbor_token(self, token: str) -> Dict[str, Any]:
        """Classify token according to CBOR major types."""
        # CBOR Major Types:
        # 0: unsigned integer
        # 1: negative integer  
        # 2: byte string
        # 3: text string
        # 4: array
        # 5: map
        # 6: semantic tag
        # 7: floating-point, simple values

        if token.startswith('"') and token.endswith('"'):
            return {
                'major_type': 3,  # text string
                'value': token[1:-1],
                'raw': token
            }
        elif token.isdigit():
            return {
                'major_type': 0,  # unsigned integer
                'value': int(token),
                'raw': token
            }
        elif token.startswith('-') and token[1:].isdigit():
            return {
                'major_type': 1,  # negative integer
                'value': int(token),
                'raw': token
            }
        elif token.lower() in ['true', 'false']:
            return {
                'major_type': 7,  # simple value (boolean)
                'value': token.lower() == 'true',
                'raw': token
            }
        elif token.lower() == 'null':
            return {
                'major_type': 7,  # simple value (null)
                'value': None,
                'raw': token
            }
        elif '.' in token:
            try:
                return {
                    'major_type': 7,  # floating-point
                    'value': float(token),
                    'raw': token
                }
            except ValueError:
                pass

        # Default to text string
        return {
            'major_type': 3,
            'value': token,
            'raw': token
        }

    def _process_cbor_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        """Process CBOR-style tokens into JSON objects."""
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.get('value') == '{':
                # Start of map (CBOR major type 5)
                map_end = self._find_map_end_cbor(tokens, i)
                if map_end > i:
                    map_tokens = tokens[i:map_end + 1]
                    parsed_map = self._parse_cbor_map(map_tokens)

                    if parsed_map:
                        complete_pairs = self._extract_complete_pairs_cbor(parsed_map)
                        self.parsed_data.update(complete_pairs)

                    i = map_end + 1
                else:
                    i += 1
            else:
                i += 1

    def _find_map_end_cbor(self, tokens: List[Dict[str, Any]], start_index: int) -> int:
        """Find end of CBOR map."""
        brace_count = 0

        for i in range(start_index, len(tokens)):
            token = tokens[i]
            value = token.get('value')

            if value == '{':
                brace_count += 1
            elif value == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i

        return -1

    def _parse_cbor_map(self, map_tokens: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse CBOR map tokens into dictionary."""
        try:
            # Reconstruct JSON from CBOR tokens
            json_parts = []

            for token in map_tokens:
                if token.get('major_type') == 'structural':
                    json_parts.append(token['value'])
                elif token.get('major_type') == 3:  # text string
                    json_parts.append(f'"{token["value"]}"')
                elif token.get('major_type') in [0, 1, 7]:  # numbers, booleans, null
                    if token['value'] is None:
                        json_parts.append('null')
                    elif isinstance(token['value'], bool):
                        json_parts.append('true' if token['value'] else 'false')
                    else:
                        json_parts.append(str(token['value']))
                else:
                    json_parts.append(token.get('raw', ''))

            # Join and parse
            json_str = ''.join(json_parts)
            json_str = self._fix_cbor_json_string(json_str)

            obj = json.loads(json_str)
            return obj if isinstance(obj, dict) else None

        except (json.JSONDecodeError, ValueError):
            # Try partial CBOR reconstruction
            return self._try_partial_cbor_reconstruction(map_tokens)

    def _fix_cbor_json_string(self, json_str: str) -> str:
        """Fix JSON string for CBOR-style parsing."""
        import re

        # Add missing colons and commas
        json_str = re.sub(r'"\s*"', '":"', json_str)  # Fix missing colons
        json_str = re.sub(r'}\s*"', '},"', json_str)  # Fix missing commas
        json_str = re.sub(r'"\s*{', '",{', json_str)  # Fix missing commas

        return json_str

    def _try_partial_cbor_reconstruction(self, map_tokens: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Try partial reconstruction of CBOR map."""
        try:
            result = {}
            i = 1  # Skip opening brace

            while i < len(map_tokens) - 1:  # Skip closing brace
                # Look for key (text string)
                if (i < len(map_tokens) and
                        map_tokens[i].get('major_type') == 3):  # text string

                    key = map_tokens[i]['value']

                    # Look for colon
                    if (i + 1 < len(map_tokens) and
                            map_tokens[i + 1].get('value') == ':'):

                        # Look for value
                        if i + 2 < len(map_tokens):
                            value_token = map_tokens[i + 2]
                            value = value_token.get('value')

                            # Store the key-value pair
                            result[key] = value
                            i += 3  # Move past key, colon, value

                            # Skip comma if present
                            if (i < len(map_tokens) and
                                    map_tokens[i].get('value') == ','):
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

    def _extract_complete_pairs_cbor(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with CBOR-style validation."""
        complete_pairs = {}

        for key, value in obj.items():
            # CBOR validation: keys must be text strings (major type 3)
            if isinstance(key, str) and len(key) > 0:
                # CBOR supports all JSON types plus additional ones
                if self._is_valid_cbor_value(value):
                    complete_pairs[key] = value

        return complete_pairs

    def _is_valid_cbor_value(self, value: Any) -> bool:
        """Check if value is valid for CBOR encoding."""
        # CBOR supports all JSON types plus binary data, tags, etc.
        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(self._is_valid_cbor_value(item) for item in value)
        if isinstance(value, dict):
            return all(isinstance(k, str) and self._is_valid_cbor_value(v)
                       for k, v in value.items())

        return False

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()
