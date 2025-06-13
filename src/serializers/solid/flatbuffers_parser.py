
"""
FlatBuffers streaming parser implementation with SOLID principles.

This module implements a streaming JSON parser inspired by FlatBuffers flat memory layout.
It follows SOLID principles with clean separation of concerns, stateless operations where possible,
and cognitive complexity under 14 for all methods.

Key Features:
- Flat memory layout inspired by FlatBuffers
- Incremental JSON parsing with token-based processing
- Stateless utility functions and processors
- Clean separation between tokenization, parsing, and data extraction
- Comprehensive error handling and recovery

Architecture:
- ParserState: Immutable state container using @dataclass
- Static utility classes for token validation and object processing
- Dependency injection for loose coupling
- Single responsibility principle throughout
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List


@dataclass
class ParserState:
    """Immutable state container for the FlatBuffers parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


class TokenValidator:
    """Stateless validator for FlatBuffers-style tokens."""

    @staticmethod
    def is_valid_token(token: str) -> bool:
        """Validate if a token is valid for processing."""
        return isinstance(token, str) and len(token.strip()) > 0

    @staticmethod
    def is_structural_token(token: str) -> bool:
        """Check if token is a structural JSON element."""
        return token.strip() in '{}[],:'

    @staticmethod
    def is_string_token(token: str) -> bool:
        """Check if token represents a string value."""
        return token.startswith('"') and token.endswith('"')


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
            if TokenValidator.is_valid_token(str(key))
        }


class FlatTokenizer:
    """Handles tokenization with FlatBuffers-inspired flat processing."""

    @staticmethod
    def tokenize(buffer: str) -> List[str]:
        """Tokenize buffer into flat token representation."""
        if not buffer:
            return []

        tokenizer = TokenizerState()

        for char in buffer:
            tokenizer.process_character(char)

        tokenizer.finalize()
        return tokenizer.get_tokens()

    @staticmethod
    def _is_delimiter(char: str) -> bool:
        """Check if character is a token delimiter."""
        return char in '{}[],:\n\r\t '


class TokenizerState:
    """Handles tokenization state for FlatTokenizer."""

    def __init__(self):
        self.tokens = []
        self.current_token = ""
        self.in_string = False
        self.escape_next = False

    def process_character(self, char: str) -> None:
        """Process a single character."""
        if self.escape_next:
            self._handle_escaped_char(char)
            return

        if char == '\\':
            self._handle_escape_char(char)
            return

        if char == '"':
            self._handle_quote_char(char)
            return

        if self.in_string:
            self.current_token += char
            return

        self._handle_non_string_char(char)

    def _handle_escaped_char(self, char: str) -> None:
        """Handle escaped character."""
        self.current_token += char
        self.escape_next = False

    def _handle_escape_char(self, char: str) -> None:
        """Handle escape character."""
        self.current_token += char
        self.escape_next = True

    def _handle_quote_char(self, char: str) -> None:
        """Handle quote character."""
        self.current_token += char
        self.in_string = not self.in_string

    def _handle_non_string_char(self, char: str) -> None:
        """Handle character outside of strings."""
        if FlatTokenizer._is_delimiter(char):
            self._handle_delimiter(char)
        else:
            self.current_token += char

    def _handle_delimiter(self, char: str) -> None:
        """Handle delimiter character."""
        if self.current_token.strip():
            self.tokens.append(self.current_token.strip())
            self.current_token = ""
        if char.strip() and char in '{}[],':
            self.tokens.append(char)

    def finalize(self) -> None:
        """Finalize tokenization."""
        if self.current_token.strip():
            self.tokens.append(self.current_token.strip())

    def get_tokens(self) -> List[str]:
        """Get the list of tokens."""
        return self.tokens


class ObjectBoundaryFinder:
    """Finds object boundaries in flat token arrays."""

    @staticmethod
    def find_object_boundaries(tokens: List[str]) -> List[tuple]:
        """Find start and end positions of complete objects."""
        boundaries = []
        i = 0

        while i < len(tokens):
            if tokens[i] == '{':
                end_pos = ObjectBoundaryFinder._find_matching_brace(tokens, i)
                if end_pos > i:
                    boundaries.append((i, end_pos))
                    i = end_pos + 1
                else:
                    i += 1
            else:
                i += 1

        return boundaries

    @staticmethod
    def _find_matching_brace(tokens: List[str], start: int) -> int:
        """Find matching closing brace for opening brace at start position."""
        brace_count = 0
        in_string = False

        for i in range(start, len(tokens)):
            token = tokens[i]

            if TokenValidator.is_string_token(token):
                in_string = not in_string
                continue

            if not in_string:
                if token == '{':
                    brace_count += 1
                elif token == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i

        return -1


class ObjectReconstructor:
    """Reconstructs JSON objects from flat token sequences."""

    @staticmethod
    def reconstruct_object(tokens: List[str], start: int, end: int) -> Optional[Dict[str, Any]]:
        """Reconstruct JSON object from token sequence."""
        if start >= end or start < 0 or end >= len(tokens):
            return None

        obj_tokens = tokens[start:end + 1]
        json_str = ObjectReconstructor._build_json_string(obj_tokens)

        return ObjectReconstructor._parse_json_string(json_str)

    @staticmethod
    def _build_json_string(tokens: List[str]) -> str:
        """Build JSON string from tokens with proper spacing."""
        if not tokens:
            return ""

        result = ""
        for i, token in enumerate(tokens):
            if TokenValidator.is_structural_token(token):
                if token == ':':
                    result += ':'
                elif token == ',':
                    result += ','
                else:
                    result += token
            else:
                if i > 0 and not tokens[i - 1] in '{[,:':
                    result += ' '
                result += token

        return result

    @staticmethod
    def _parse_json_string(json_str: str) -> Optional[Dict[str, Any]]:
        """Parse JSON string into dictionary."""
        try:
            obj = json.loads(json_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return ObjectReconstructor._try_partial_parse(json_str)

    @staticmethod
    def _try_partial_parse(json_str: str) -> Optional[Dict[str, Any]]:
        """Try partial parsing with brace balancing."""
        if '{' not in json_str:
            return None

        open_braces = json_str.count('{')
        close_braces = json_str.count('}')

        if open_braces > close_braces:
            balanced_str = json_str + '}' * (open_braces - close_braces)
            try:
                obj = json.loads(balanced_str)
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                pass

        return None


class FlatBufferProcessor:
    """Main processor using FlatBuffers-inspired flat memory layout with dependency injection."""

    def __init__(self,
                 tokenizer: FlatTokenizer = None,
                 boundary_finder: ObjectBoundaryFinder = None,
                 reconstructor: ObjectReconstructor = None,
                 pair_extractor: PairExtractor = None):
        self._tokenizer = tokenizer or FlatTokenizer()
        self._boundary_finder = boundary_finder or ObjectBoundaryFinder()
        self._reconstructor = reconstructor or ObjectReconstructor()
        self._pair_extractor = pair_extractor or PairExtractor()

    def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Process buffer using flat memory layout approach."""
        tokens = self._tokenizer.tokenize(buffer)
        if not tokens:
            return {}

        boundaries = self._boundary_finder.find_object_boundaries(tokens)
        parsed_data = {}

        for start, end in boundaries:
            obj = self._reconstructor.reconstruct_object(tokens, start, end)
            if obj:
                complete_pairs = self._pair_extractor.extract_complete_pairs(obj)
                parsed_data.update(complete_pairs)

        return parsed_data


class StreamingJsonParser:
    """Streaming JSON parser with FlatBuffers-inspired flat memory layout."""

    def __init__(self, processor: FlatBufferProcessor = None):
        """Initialize the streaming JSON parser with dependency injection."""
        self._state = ParserState()
        self._processor = processor or FlatBufferProcessor()

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
        Process a chunk of JSON data incrementally using FlatBuffers-style layout.

        Args:
            buffer: String chunk of JSON data to process
        """
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
