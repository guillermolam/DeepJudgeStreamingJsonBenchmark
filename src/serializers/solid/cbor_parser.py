"""
CBOR (Concise Binary Object Representation) streaming parser implementation.
Note: CBOR is a binary format, so this implements JSON parsing
with CBOR-inspired compact encoding and streaming concepts.
"""
import json
from typing import Any, Dict, Optional, List


class StreamingJsonParser:
    """Streaming JSON parser with CBOR-inspired compact encoding and streaming."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._reset_state()
        self._initialize_cbor_types()

    def _reset_state(self) -> None:
        """Reset parser state to initial values."""
        self.buffer = ""
        self.parsed_data = {}
        self.compact_buffer = []

    def _initialize_cbor_types(self) -> None:
        """Initialize CBOR major type mappings."""
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
        Process a chunk of JSON data_gen incrementally using CBOR-style processing.

        Args:
            buffer: String chunk of JSON data_gen to process
        """
        self._append_to_buffer(buffer)
        self._process_buffer()

    def _append_to_buffer(self, buffer: str) -> None:
        """Append new data_gen to internal buffer."""
        self.buffer += buffer

    def _process_buffer(self) -> None:
        """Process the current buffer content."""
        tokens = self._create_tokens()
        self._update_parsed_data(tokens)

    def _create_tokens(self) -> List[Dict[str, Any]]:
        """Create CBOR-style tokens from buffer."""
        return self._tokenize_cbor_style()

    def _update_parsed_data(self, tokens: List[Dict[str, Any]]) -> None:
        """Update parsed data_gen with new tokens."""
        self._process_cbor_tokens(tokens)

    def _tokenize_cbor_style(self) -> List[Dict[str, Any]]:
        """Tokenize buffer into CBOR-style data_gen items."""
        tokenizer = CborTokenizer(self.buffer)
        return tokenizer.tokenize()

    def _process_cbor_tokens(self, tokens: List[Dict[str, Any]]) -> None:
        """Process CBOR-style tokens into JSON objects."""
        processor = CborTokenProcessor()
        maps = processor.extract_maps(tokens)

        for parsed_map in maps:
            if parsed_map:
                complete_pairs = self._get_complete_pairs(parsed_map)
                self.parsed_data.update(complete_pairs)

    @staticmethod
    def _get_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with CBOR-style validation."""
        validator = CborValidator()
        return validator.extract_complete_pairs(obj)

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()


class CborTokenizer:
    """Handles tokenization of buffer into CBOR-style tokens."""

    def __init__(self, buffer: str):
        self.buffer = buffer
        self.tokens = []
        self.current_token = ""
        self.in_string = False
        self.escape_next = False

    def tokenize(self) -> List[Dict[str, Any]]:
        """Tokenize the buffer into CBOR-style tokens."""
        self._process_characters()
        self._finalize_token()
        return self.tokens

    def _process_characters(self) -> None:
        """Process each character in the buffer."""
        for char in self.buffer:
            self._process_character(char)

    def _process_character(self, char: str) -> None:
        """Process a single character."""
        if self._handle_escape_sequence(char):
            return

        if self._handle_quote(char):
            return

        if self._handle_non_string_character(char):
            return

        self._append_to_token(char)

    def _handle_escape_sequence(self, char: str) -> bool:
        """Handle escape sequences in strings."""
        if self.escape_next:
            self.current_token += char
            self.escape_next = False
            return True

        if char == '\\':
            self.current_token += char
            self.escape_next = True
            return True

        return False

    def _handle_quote(self, char: str) -> bool:
        """Handle quote characters."""
        if char != '"':
            return False

        self.current_token += char
        if not self.escape_next:
            self.in_string = not self.in_string

            if self._is_complete_string():
                self._add_string_token()

        return True

    def _is_complete_string(self) -> bool:
        """Check if the current token is a complete string."""
        return not self.in_string and self.current_token.startswith('"')

    def _add_string_token(self) -> None:
        """Add a complete string token."""
        token = self._create_string_token()
        self.tokens.append(token)
        self.current_token = ""

    def _create_string_token(self) -> Dict[str, Any]:
        """Create a string token."""
        return {
            'major_type': 3,  # text string
            'value': self.current_token[1:-1],  # Remove quotes
            'raw': self.current_token
        }

    def _handle_non_string_character(self, char: str) -> bool:
        """Handle characters outside of strings."""
        if self.in_string:
            return False

        if self._is_delimiter(char):
            self._handle_delimiter(char)
            return True

        return False

    @staticmethod
    def _is_delimiter(char: str) -> bool:
        """Check if character is a delimiter."""
        return char in '{}[],:\n\r\t '

    def _handle_delimiter(self, char: str) -> None:
        """Handle delimiter characters."""
        self._finalize_current_token()

        if self._is_structural_character(char):
            self._add_structural_token(char)

    @staticmethod
    def _is_structural_character(char: str) -> bool:
        """Check if the character is structural."""
        return char.strip() and char in '{}[],'

    def _add_structural_token(self, char: str) -> None:
        """Add a structural token."""
        token = {
            'major_type': 'structural',
            'value': char,
            'raw': char
        }
        self.tokens.append(token)

    def _finalize_current_token(self) -> None:
        """Finalize the current token if it exists."""
        if self.current_token.strip():
            token = self._classify_token(self.current_token.strip())
            self.tokens.append(token)
            self.current_token = ""

    def _append_to_token(self, char: str) -> None:
        """Append character to current token."""
        self.current_token += char

    def _finalize_token(self) -> None:
        """Finalize any remaining token."""
        if self.current_token.strip():
            token = self._classify_token(self.current_token.strip())
            self.tokens.append(token)

    @staticmethod
    def _classify_token(token: str) -> Dict[str, Any]:
        """Classify token according to CBOR major types."""
        classifier = TokenClassifier()
        return classifier.classify(token)


class TokenClassifier:
    """Classifies tokens according to CBOR major types."""

    def classify(self, token: str) -> Dict[str, Any]:
        """Classify a token into CBOR major type."""
        if self._is_quoted_string(token):
            return self._create_text_string_token(token)

        if self._is_unsigned_integer(token):
            return self._create_unsigned_int_token(token)

        if self._is_negative_integer(token):
            return self._create_negative_int_token(token)

        if self._is_boolean(token):
            return self._create_boolean_token(token)

        if self._is_null(token):
            return self._create_null_token()

        if self._is_float(token):
            return self._create_float_token(token)

        return self._create_default_token(token)

    @staticmethod
    def _is_quoted_string(token: str) -> bool:
        """Check if the token is a quoted string."""
        return token.startswith('"') and token.endswith('"')

    @staticmethod
    def _is_unsigned_integer(token: str) -> bool:
        """Check if token is an unsigned integer."""
        return token.isdigit()

    @staticmethod
    def _is_negative_integer(token: str) -> bool:
        """Check if token is a negative integer."""
        return token.startswith('-') and token[1:].isdigit()

    @staticmethod
    def _is_boolean(token: str) -> bool:
        """Check if the token is a boolean."""
        return token.lower() in ['true', 'false']

    @staticmethod
    def _is_null(token: str) -> bool:
        """Check if the token is null."""
        return token.lower() == 'null'

    @staticmethod
    def _is_float(token: str) -> bool:
        """Check if the token is a float."""
        if '.' not in token:
            return False
        try:
            float(token)
            return True
        except ValueError:
            return False

    @staticmethod
    def _create_text_string_token(token: str) -> Dict[str, Any]:
        """Create a text string token."""
        return {
            'major_type': 3,  # text string
            'value': token[1:-1],
            'raw': token
        }

    @staticmethod
    def _create_unsigned_int_token(token: str) -> Dict[str, Any]:
        """Create an unsigned integer token."""
        return {
            'major_type': 0,  # unsigned integer
            'value': int(token),
            'raw': token
        }

    @staticmethod
    def _create_negative_int_token(token: str) -> Dict[str, Any]:
        """Create a negative integer token."""
        return {
            'major_type': 1,  # negative integer
            'value': int(token),
            'raw': token
        }

    @staticmethod
    def _create_boolean_token(token: str) -> Dict[str, Any]:
        """Create a boolean token."""
        return {
            'major_type': 7,  # simple value (boolean)
            'value': token.lower() == 'true',
            'raw': token
        }

    @staticmethod
    def _create_null_token() -> Dict[str, Any]:
        """Create a null token."""
        return {
            'major_type': 7,  # simple value (null)
            'value': None,
            'raw': 'null'
        }

    @staticmethod
    def _create_float_token(token: str) -> Dict[str, Any]:
        """Create a float token."""
        return {
            'major_type': 7,  # floating-point
            'value': float(token),
            'raw': token
        }

    @staticmethod
    def _create_default_token(token: str) -> Dict[str, Any]:
        """Create a default text string token."""
        return {
            'major_type': 3,
            'value': token,
            'raw': token
        }


class CborTokenProcessor:
    """Processes CBOR tokens into structured data_gen."""

    def extract_maps(self, tokens: List[Dict[str, Any]]) -> List[Optional[Dict[str, Any]]]:
        """Extract all maps from tokens."""
        maps = []
        i = 0

        while i < len(tokens):
            if self._is_map_start(tokens[i]):
                map_result, next_index = self._process_map(tokens, i)
                maps.append(map_result)
                i = next_index
            else:
                i += 1

        return maps

    @staticmethod
    def _is_map_start(token: Dict[str, Any]) -> bool:
        """Check if token starts a map."""
        return token.get('value') == '{'

    def _process_map(self, tokens: List[Dict[str, Any]], start_index: int) -> tuple:
        """Process a single map from tokens."""
        map_end = self._find_map_end(tokens, start_index)

        if map_end > start_index:
            map_tokens = tokens[start_index:map_end + 1]
            parsed_map = self._parse_map_tokens(map_tokens)
            return parsed_map, map_end + 1

        return None, start_index + 1

    @staticmethod
    def _find_map_end(tokens: List[Dict[str, Any]], start_index: int) -> int:
        """Find the end index of a map."""
        brace_counter = BraceCounter()
        return brace_counter.find_end(tokens, start_index)

    @staticmethod
    def _parse_map_tokens(map_tokens: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse map tokens into a dictionary."""
        parser = MapTokenParser()
        return parser.parse(map_tokens)


class BraceCounter:
    """Counts braces to find map boundaries."""

    @staticmethod
    def find_end(tokens: List[Dict[str, Any]], start_index: int) -> int:
        """Find the end of a brace-delimited structure."""
        brace_count = 0

        for i in range(start_index, len(tokens)):
            value = tokens[i].get('value')

            if value == '{':
                brace_count += 1
            elif value == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i

        return -1


class MapTokenParser:
    """Parses map tokens into dictionaries."""

    def parse(self, map_tokens: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse map tokens into a dictionary."""
        try:
            json_str = self._reconstruct_json(map_tokens)
            return self._parse_json_string(json_str)
        except json.JSONDecodeError:
            return self._try_partial_reconstruction(map_tokens)
        except ValueError:
            return self._try_partial_reconstruction(map_tokens)

    @staticmethod
    def _reconstruct_json(map_tokens: List[Dict[str, Any]]) -> str:
        """Reconstruct a JSON string from map tokens."""
        reconstructor = JsonReconstructor()
        return reconstructor.reconstruct(map_tokens)

    @staticmethod
    def _parse_json_string(json_str: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON string into a dictionary."""
        obj = json.loads(json_str)
        return obj if isinstance(obj, dict) else None

    @staticmethod
    def _try_partial_reconstruction(map_tokens: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Try to reconstruct a partial map from tokens."""
        reconstructor = PartialMapReconstructor()
        return reconstructor.reconstruct(map_tokens)


class JsonReconstructor:
    """Reconstructs JSON strings from tokens."""

    def reconstruct(self, map_tokens: List[Dict[str, Any]]) -> str:
        """Reconstruct JSON string from map tokens."""
        json_parts = self._build_json_parts(map_tokens)
        json_str = ''.join(json_parts)
        return self._fix_json_string(json_str)

    def _build_json_parts(self, map_tokens: List[Dict[str, Any]]) -> List[str]:
        """Build JSON parts from tokens."""
        json_parts = []

        for token in map_tokens:
            part = self._convert_token_to_json(token)
            json_parts.append(part)

        return json_parts

    @staticmethod
    def _convert_token_to_json(token: Dict[str, Any]) -> str:
        """Convert a single token to JSON representation."""
        major_type = token.get('major_type')
        value = token.get('value')

        if major_type == 'structural':
            return value
        elif major_type == 3:  # text string
            return f'"{value}"'
        elif major_type in [0, 1, 7]:  # numbers, booleans, null
            return JsonReconstructor._format_primitive_value(value)
        else:
            return token.get('../raw', '')

    @staticmethod
    def _format_primitive_value(value: Any) -> str:
        """Format primitive values for JSON."""
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        else:
            return str(value)

    @staticmethod
    def _fix_json_string(json_str: str) -> str:
        """Fix common JSON string issues."""
        import re

        # Add missing colons and commas
        json_str = re.sub(r'"\s*"', '":"', json_str)
        json_str = re.sub(r'}\s*"', '},"', json_str)
        json_str = re.sub(r'"\s*{', '",{', json_str)

        return json_str


class PartialMapReconstructor:
    """Reconstructs partial maps from tokens."""

    def reconstruct(self, map_tokens: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Reconstruct a partial map from tokens."""
        try:
            result = {}
            i = 1  # Skip opening brace

            while i < len(map_tokens) - 1:  # Skip closing brace
                key_value_pair, next_index = self._extract_key_value_pair(map_tokens, i)

                if key_value_pair:
                    key, value = key_value_pair
                    result[key] = value
                    i = next_index
                else:
                    i += 1

            return result if result else None

        except (IndexError, KeyError, TypeError):
            return None

    @staticmethod
    def _extract_key_value_pair(tokens: List[Dict[str, Any]], index: int) -> tuple:
        """Extract a key-value pair starting at the given index."""
        if not PartialMapReconstructor._is_valid_key_token(tokens, index):
            return None, index + 1

        key = tokens[index]['value']

        if not PartialMapReconstructor._has_colon_separator(tokens, index):
            return None, index + 1

        if not PartialMapReconstructor._has_value_token(tokens, index):
            return None, index + 3

        value = tokens[index + 2]['value']
        next_index = PartialMapReconstructor._skip_comma(tokens, index + 3)

        return (key, value), next_index

    @staticmethod
    def _is_valid_key_token(tokens: List[Dict[str, Any]], index: int) -> bool:
        """Check if token at index is a valid key."""
        return (index < len(tokens) and
                tokens[index].get('major_type') == 3)

    @staticmethod
    def _has_colon_separator(tokens: List[Dict[str, Any]], key_index: int) -> bool:
        """Check if there's a colon after the key."""
        colon_index = key_index + 1
        return (colon_index < len(tokens) and
                tokens[colon_index].get('value') == ':')

    @staticmethod
    def _has_value_token(tokens: List[Dict[str, Any]], key_index: int) -> bool:
        """Check if there's a value token after the colon."""
        value_index = key_index + 2
        return value_index < len(tokens)

    @staticmethod
    def _skip_comma(tokens: List[Dict[str, Any]], index: int) -> int:
        """Skip comma if present and return the next index."""
        if (index < len(tokens) and
                tokens[index].get('value') == ','):
            return index + 1
        return index


class CborValidator:
    """Validates CBOR data_gen structures."""

    def extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with CBOR-style validation."""
        complete_pairs = {}

        for key, value in obj.items():
            if self._is_valid_key(key) and self._is_valid_cbor_value(value):
                complete_pairs[key] = value

        return complete_pairs

    @staticmethod
    def _is_valid_key(key: Any) -> bool:
        """Check if the key is valid for CBOR."""
        return isinstance(key, str) and len(key) > 0

    def _is_valid_cbor_value(self, value: Any) -> bool:
        """Check if the value is valid for CBOR encoding."""
        if self._is_primitive_value(value):
            return True
        elif isinstance(value, list):
            return self._is_valid_array(value)
        elif isinstance(value, dict):
            return self._is_valid_object(value)

        return False

    @staticmethod
    def _is_primitive_value(value: Any) -> bool:
        """Check if value is a primitive type."""
        return (value is None or
                isinstance(value, (str, int, float, bool)))

    def _is_valid_array(self, array: List[Any]) -> bool:
        """Check if array contains valid CBOR values."""
        return all(self._is_valid_cbor_value(item) for item in array)

    def _is_valid_object(self, obj: Dict[str, Any]) -> bool:
        """Check if object contains valid CBOR key-value pairs."""
        return all(isinstance(k, str) and self._is_valid_cbor_value(v)
                   for k, v in obj.items())
