"""
FlatBuffers streaming parser implementation.
Note: FlatBuffers is for binary serialization with zero-copy access,
so this implements JSON parsing with FlatBuffers-inspired flat memory layout concepts.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List


@dataclass
class ParserState:
    """Internal state for FlatBuffers parser."""

    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    flat_buffer: List[str] = field(default_factory=list)
    offset_table: Dict[int, int] = field(default_factory=dict)
    current_offset: int = 0


class StreamingJsonParser:
    """Streaming JSON parser with FlatBuffers-inspired flat memory layout."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._state = ParserState()
        self._initialize_flat_buffer()

    @property
    def buffer(self) -> str:
        return self._state.buffer

    @buffer.setter
    def buffer(self, value: str) -> None:
        self._state.buffer = value

    @property
    def parsed_data(self) -> Dict[str, Any]:
        return self._state.parsed_data

    @property
    def flat_buffer(self) -> List[str]:
        return self._state.flat_buffer

    @flat_buffer.setter
    def flat_buffer(self, value: List[str]) -> None:
        self._state.flat_buffer = value

    @property
    def offset_table(self) -> Dict[int, int]:
        return self._state.offset_table

    @offset_table.setter
    def offset_table(self, value: Dict[int, int]) -> None:
        self._state.offset_table = value

    @property
    def current_offset(self) -> int:
        return self._state.current_offset

    @current_offset.setter
    def current_offset(self, value: int) -> None:
        self._state.current_offset = value

    def _reset_state(self) -> None:
        """Reset parser state to initial values."""
        self._state.buffer = ""
        self._state.parsed_data.clear()

    def _initialize_flat_buffer(self) -> None:
        """Initialize FlatBuffers-style data_gen structures."""
        self._state.flat_buffer = []  # Flat representation of data_gen
        self._state.offset_table = {}
        self._state.current_offset = 0

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data_gen incrementally using FlatBuffers-style layout.

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
        self._parse_flat_buffer_style()

    def _parse_flat_buffer_style(self) -> None:
        """Parse using FlatBuffers-inspired flat memory layout."""
        self._build_flat_representation()
        self._parse_from_flat_buffer()

    def _build_flat_representation(self) -> None:
        """Build flat representation of the JSON data_gen."""
        tokens = self._create_tokens()
        self._add_tokens_to_flat_buffer(tokens)

    def _create_tokens(self) -> List[str]:
        """Create tokens from buffer."""
        tokenizer = FlatBufferTokenizer(self.buffer)
        return tokenizer.tokenize()

    def _add_tokens_to_flat_buffer(self, tokens: List[str]) -> None:
        """Add tokens to flat buffer with offsets."""
        for token in tokens:
            self.flat_buffer.append(token)
            self.offset_table[self.current_offset] = len(self.flat_buffer) - 1
            self.current_offset += 1

    def _parse_from_flat_buffer(self) -> None:
        """Parse JSON objects from flat buffer representation."""
        processor = FlatBufferProcessor(self.flat_buffer)
        objects = processor.extract_objects()

        for parsed_obj in objects:
            if parsed_obj:
                complete_pairs = self._get_complete_pairs(parsed_obj)
                self.parsed_data.update(complete_pairs)

    @staticmethod
    def _get_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with FlatBuffers-style validation."""
        validator = FlatBufferValidator()
        return validator.extract_complete_pairs(obj)

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self._sorted_copy(self.parsed_data)

    @staticmethod
    def _sorted_copy(data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a dict sorted by keys for deterministic output."""
        return {k: data[k] for k in sorted(data.keys())}


class FlatBufferValidator:
    """Validates and extracts complete key-value pairs."""

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only complete key-value pairs."""
        return obj  # For now, return all pairs


class FlatBufferTokenizer:
    """Handles tokenization of buffer into FlatBuffers-style tokens."""

    def __init__(self, buffer: str):
        self.buffer = buffer
        self.tokens = []
        self.current_token = ""
        self.in_string = False
        self.escape_next = False

    def tokenize(self) -> List[str]:
        """Tokenize the buffer into FlatBuffers-style tokens."""
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

        return True

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
            self._add_token(char)

    @staticmethod
    def _is_structural_character(char: str) -> bool:
        """Check if the character is structural."""
        return char.strip() and char in '{}[],:'

    def _finalize_current_token(self) -> None:
        """Finalize the current token if it exists."""
        if self.current_token.strip():
            self._add_token(self.current_token.strip())
            self.current_token = ""

    def _add_token(self, token: str) -> None:
        """Add a token to the token list."""
        self.tokens.append(token)

    def _append_to_token(self, char: str) -> None:
        """Append character to current token."""
        self.current_token += char

    def _finalize_token(self) -> None:
        """Finalize any remaining token."""
        if self.current_token.strip():
            self._add_token(self.current_token.strip())


class FlatBufferProcessor:
    """Processes FlatBuffer tokens into structured data_gen."""

    def __init__(self, flat_buffer: List[str]):
        self.flat_buffer = flat_buffer

    def extract_objects(self) -> List[Optional[Dict[str, Any]]]:
        """Extract all objects from flat buffer."""
        objects = []
        i = 0

        while i < len(self.flat_buffer):
            if self._is_object_start(i):
                obj_result, next_index = self._process_object(i)
                objects.append(obj_result)
                i = next_index
            else:
                i += 1

        return objects

    def _is_object_start(self, index: int) -> bool:
        """Check if token at index starts an object."""
        return (index < len(self.flat_buffer) and
                self.flat_buffer[index] == '{')

    def _process_object(self, start_index: int) -> tuple:
        """Process a single object from flat buffer."""
        obj_end = self._find_object_end(start_index)

        if obj_end > start_index:
            obj_tokens = self.flat_buffer[start_index:obj_end + 1]
            parsed_obj = self._reconstruct_object(obj_tokens)
            return parsed_obj, obj_end + 1

        return None, start_index + 1

    def _find_object_end(self, start_index: int) -> int:
        """Find the end of an object in flat buffer."""
        finder = ObjectEndFinder(self.flat_buffer)
        return finder.find_end(start_index)

    @staticmethod
    def _reconstruct_object(obj_tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Reconstruct JSON object from flat tokens."""
        reconstructor = ObjectReconstructor()
        return reconstructor.reconstruct(obj_tokens)


class ObjectEndFinder:
    """Finds the end of objects in flat buffer using FlatBuffers-style navigation."""

    def __init__(self, flat_buffer: List[str]):
        self.flat_buffer = flat_buffer

    def find_end(self, start_index: int) -> int:
        """Find the end of an object in flat buffer."""
        brace_count = 0
        in_string = False

        for i in range(start_index, len(self.flat_buffer)):
            token = self.flat_buffer[i]

            if self._is_string_delimiter(token):
                in_string = not in_string
                continue

            if not in_string:
                if self._is_opening_brace(token):
                    brace_count += 1
                elif self._is_closing_brace(token):
                    brace_count -= 1
                    if brace_count == 0:
                        return i

        return -1

    @staticmethod
    def _is_string_delimiter(token: str) -> bool:
        """Check if token is a string delimiter."""
        return token == '"'

    @staticmethod
    def _is_opening_brace(token: str) -> bool:
        """Check if token is an opening brace."""
        return token == '{'

    @staticmethod
    def _is_closing_brace(token: str) -> bool:
        """Check if token is a closing brace."""
        return token == '}'


class ObjectReconstructor:
    """Reconstructs JSON objects from flat tokens."""

    def reconstruct(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Reconstruct JSON object from flat tokens."""
        try:
            json_str = self._build_json_string(tokens)
            return self._parse_json_string(json_str)
        except json.JSONDecodeError:
            return self._try_partial_reconstruction(tokens)

    @staticmethod
    def _build_json_string(tokens: List[str]) -> str:
        """Build JSON string from tokens."""
        builder = JsonStringBuilder()
        return builder.build(tokens)

    @staticmethod
    def _parse_json_string(json_str: str) -> Optional[Dict[str, Any]]:
        """Parse JSON string into dictionary."""
        obj = json.loads(json_str)
        return obj if isinstance(obj, dict) else None

    @staticmethod
    def _try_partial_reconstruction(tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Try partial reconstruction of incomplete objects."""
        reconstructor = PartialObjectReconstructor()
        return reconstructor.reconstruct(tokens)


class JsonStringBuilder:
    """Builds JSON strings from tokens."""

    def build(self, tokens: List[str]) -> str:
        """Build JSON string from tokens."""
        json_str = self._join_tokens(tokens)
        return self._clean_json_string(json_str)

    def _join_tokens(self, tokens: List[str]) -> str:
        """Join tokens into a JSON string."""
        json_str = ""

        for token in tokens:
            if self._is_structural_token(token):
                json_str += token
            elif self._is_colon(token):
                json_str += ':'
            else:
                json_str = self._add_token_with_spacing(json_str, token)

        return json_str

    @staticmethod
    def _is_structural_token(token: str) -> bool:
        """Check if the token is structural."""
        return token in '{}[],'

    @staticmethod
    def _is_colon(token: str) -> bool:
        """Check if the token is a colon."""
        return token == ':'

    @staticmethod
    def _add_token_with_spacing(json_str: str, token: str) -> str:
        """Add token with appropriate spacing."""
        if json_str and json_str[-1] not in '{"[,:':
            json_str += ' '
        json_str += token
        return json_str

    @staticmethod
    def _clean_json_string(json_str: str) -> str:
        """Clean up JSON string for parsing."""
        import re

        # Fix spacing around colons and commas
        json_str = re.sub(r'\s*:\s*', ':', json_str)
        json_str = re.sub(r'\s*,\s*', ',', json_str)

        # Ensure proper spacing
        json_str = re.sub(r'([{,])\s*(["\w])', r'\1\2', json_str)
        json_str = re.sub(r'(["\w])\s*([,}])', r'\1\2', json_str)

        return json_str


class PartialObjectReconstructor:
    """Reconstructs partial objects from tokens."""

    def reconstruct(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Try partial reconstruction of incomplete objects."""
        try:
            result = {}
            i = 1  # Skip opening brace

            while i < len(tokens) - 1:  # Skip closing brace
                key_value_pair, next_index = self._extract_key_value_pair(tokens, i)

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
    def _extract_key_value_pair(tokens: List[str], index: int) -> tuple:
        """Extract a key-value pair starting at the given index."""
        if not PartialObjectReconstructor._is_valid_key_token(tokens, index):
            return None, index + 1

        key = PartialObjectReconstructor._extract_key(tokens[index])

        if not PartialObjectReconstructor._has_colon_separator(tokens, index):
            return None, index + 1

        if not PartialObjectReconstructor._has_value_token(tokens, index):
            return None, index + 3

        value = PartialObjectReconstructor._parse_value_token(tokens[index + 2])
        next_index = PartialObjectReconstructor._skip_comma(tokens, index + 3)

        return (key, value), next_index

    @staticmethod
    def _is_valid_key_token(tokens: List[str], index: int) -> bool:
        """Check if token at index is a valid key."""
        token = tokens[index] if index < len(tokens) else None
        return (
                token is not None and
                isinstance(token, str) and
                token.startswith('"') and
                token.endswith('"')
        )

    @staticmethod
    def _extract_key(token: str) -> str:
        """Extract key from token."""
        return token[1:-1]  # Remove quotes

    @staticmethod
    def _has_colon_separator(tokens: List[str], key_index: int) -> bool:
        """Check if there's a colon after the key."""
        colon_index = key_index + 1
        return (colon_index < len(tokens) and
                tokens[colon_index] == ':')

    @staticmethod
    def _has_value_token(tokens: List[str], key_index: int) -> bool:
        """Check if there's a value token after the colon."""
        value_index = key_index + 2
        return value_index < len(tokens)

    @staticmethod
    def _parse_value_token(value_token: str) -> Any:
        """Parse value token into the appropriate Python type."""
        try:
            if value_token is None:
                return None
            if isinstance(value_token, str) and value_token.startswith('"') and value_token.endswith('"'):
                return value_token[1:-1]  # String value
            elif isinstance(value_token, str) and value_token.lower() in ['true', 'false']:
                return value_token.lower() == 'true'
            elif isinstance(value_token, str) and value_token.lower() == 'null':
                return None
            else:
                return json.loads(value_token)  # Number or other
        except ValueError:
            return value_token  # Return as string if parsing fails

    @staticmethod
    def _skip_comma(tokens: List[str], index: int) -> int:
        """Skip comma if present and return the next index."""
        if (index < len(tokens) and
                tokens[index] == ','):
            return index + 1
        return index
