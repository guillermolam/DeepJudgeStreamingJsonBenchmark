"""
CBOR-inspired streaming JSON parser implementation with SOLID principles.

This module implements a streaming JSON parser inspired by CBOR (Concise Binary Object Representation)
tokenization and processing. It follows SOLID principles with clean separation of concerns,
stateless operations where possible, and cognitive complexity under 14 for all methods.

Key Features:
- CBOR-inspired tokenization for structured JSON parsing
- Partial object reconstruction for incomplete JSON fragments
- Stateless token classification and processing
- Clean separation between tokenization, processing, and parsing
- Comprehensive error handling and recovery

Architecture:
- Immutable token representation using @dataclass
- Static utility classes for token classification and processing
- Stateless token processing with functional approach
- Single responsibility principle throughout
- Dependency injection for loose coupling
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class CborToken:
    """Immutable representation of a CBOR-inspired token."""
    major_type: Union[int, str]
    value: Any
    raw: str


@dataclass
class TokenizeState:
    """Immutable state for tokenization process."""
    in_string: bool = False
    escape: bool = False


class TokenClassifier:
    """Stateless utility for classifying tokens according to CBOR types."""

    @staticmethod
    def classify_token(token: str) -> CborToken:
        """Classify a token string into appropriate CBOR-style token."""
        # String literal classification
        if TokenClassifier._is_string_literal(token):
            return CborToken(3, token[1:-1], token)

        # Numeric classification
        numeric_result = TokenClassifier._classify_numeric(token)
        if numeric_result:
            return numeric_result

        # Boolean and null classification
        literal_result = TokenClassifier._classify_literal(token)
        if literal_result:
            return literal_result

        # Default: bare text
        return CborToken(3, token, token)

    @staticmethod
    def _is_string_literal(token: str) -> bool:
        """Check if token is a string literal."""
        return token.startswith('"') and token.endswith('"')

    @staticmethod
    def _classify_numeric(token: str) -> Optional[CborToken]:
        """Classify numeric tokens (integers and floats)."""
        # Integer classification
        if re.fullmatch(r'-?\d+', token):
            val = int(token)
            major_type = 0 if not token.startswith('-') else 1
            return CborToken(major_type, val, token)

        # Float classification
        if re.fullmatch(r'-?\d+\.\d+', token):
            return CborToken(7, float(token), token)

        return None

    @staticmethod
    def _classify_literal(token: str) -> Optional[CborToken]:
        """Classify boolean and null literals."""
        token_lower = token.lower()
        literal_map = {'true': True, 'false': False, 'null': None}

        if token_lower in literal_map:
            return CborToken(7, literal_map[token_lower], token)

        return None


class TokenBuffer:
    """Stateless utility for managing token buffer operations."""

    @staticmethod
    def flush_to_tokens(current: List[str], tokens: List[CborToken]) -> None:
        """Flush current buffer to tokens list."""
        if not current:
            return

        token_str = ''.join(current).strip()
        current.clear()

        if token_str:
            tokens.append(TokenClassifier.classify_token(token_str))

    @staticmethod
    def is_structural_char(ch: str) -> bool:
        """Check if character is a structural JSON character."""
        return ch in '{}[],:'

    @staticmethod
    def is_whitespace(ch: str) -> bool:
        """Check if character is whitespace."""
        return ch in ' \n\r\t'


class CborTokenizer:
    """Tokenizes JSON text into CBOR-style tokens with stateless operations."""

    @staticmethod
    def tokenize(buffer: str) -> List[CborToken]:
        """Tokenize buffer into CBOR-style tokens."""
        tokens: List[CborToken] = []
        current: List[str] = []
        state = TokenizeState()

        for ch in buffer:
            state = CborTokenizer._process_character(ch, current, tokens, state)

        TokenBuffer.flush_to_tokens(current, tokens)
        return tokens

    @staticmethod
    def _process_character(ch: str, current: List[str], tokens: List[CborToken],
                           state: TokenizeState) -> TokenizeState:
        """Process a single character and return new state."""
        # Handle escape sequences
        if state.escape:
            current.append(ch)
            return TokenizeState(state.in_string, False)

        if ch == '\\':
            current.append(ch)
            return TokenizeState(state.in_string, True)

        # Handle string processing
        if state.in_string:
            return CborTokenizer._process_string_character(ch, current, tokens, state)

        # Handle non-string processing
        return CborTokenizer._process_non_string_character(ch, current, tokens, state)

    @staticmethod
    def _process_string_character(ch: str, current: List[str], tokens: List[CborToken],
                                  state: TokenizeState) -> TokenizeState:
        """Process character while inside a string."""
        current.append(ch)

        if ch == '"' and not state.escape:
            tokens.append(TokenClassifier.classify_token(''.join(current)))
            current.clear()
            return TokenizeState(False, False)

        return state

    @staticmethod
    def _process_non_string_character(ch: str, current: List[str], tokens: List[CborToken],
                                      state: TokenizeState) -> TokenizeState:
        """Process character while outside a string."""
        if ch == '"':
            current.append(ch)
            return TokenizeState(True, False)

        if TokenBuffer.is_structural_char(ch) or TokenBuffer.is_whitespace(ch):
            TokenBuffer.flush_to_tokens(current, tokens)

            if TokenBuffer.is_structural_char(ch):
                tokens.append(CborToken('structural', ch, ch))
        else:
            current.append(ch)

        return state


class MapTokenProcessor:
    """Stateless utility for processing map tokens."""

    @staticmethod
    def find_map_starts(tokens: List[CborToken]) -> List[int]:
        """Find all positions where maps start."""
        return [i for i, token in enumerate(tokens) if token.value == '{']

    @staticmethod
    def find_map_end(tokens: List[CborToken], start: int) -> int:
        """Find the end position of a map starting at given position."""
        depth = 0

        for idx in range(start, len(tokens)):
            token_value = tokens[idx].value

            if token_value == '{':
                depth += 1
            elif token_value == '}':
                depth -= 1

            if depth == 0:
                return idx

        return -1


class JsonStringBuilder:
    """Stateless utility for building JSON strings from tokens."""

    @staticmethod
    def build_json_string(segment: List[CborToken]) -> str:
        """Build JSON string from token segment."""
        return ''.join(
            token.raw if JsonStringBuilder._use_raw_token(token)
            else JsonStringBuilder._get_value_literal(token)
            for token in segment
        )

    @staticmethod
    def _use_raw_token(token: CborToken) -> bool:
        """Check if token should use raw representation."""
        return token.raw in '{}[],: '

    @staticmethod
    def _get_value_literal(token: CborToken) -> str:
        """Get literal representation of token value."""
        if token.value is None:
            return 'null'
        if isinstance(token.value, bool):
            return 'true' if token.value else 'false'
        if isinstance(token.value, str):
            return f'"{token.value}"'
        return str(token.value)

    @staticmethod
    def repair_json_string(json_str: str) -> str:
        """Repair common JSON formatting issues."""
        # Fix key-value separator spacing
        json_str = re.sub(r'"\s*"', '":"', json_str)
        # Fix object separator spacing
        json_str = re.sub(r'}\s*"', '},"', json_str)
        json_str = re.sub(r'"\s*{', '",{', json_str)
        return json_str


class PartialObjectParser:
    """Stateless utility for parsing partial objects from tokens."""

    @staticmethod
    def parse_partial_object(tokens: List[CborToken]) -> Optional[Dict[str, Any]]:
        """Parse partial object from token list."""
        result: Dict[str, Any] = {}
        index = 1  # Skip opening '{'

        while index < len(tokens):
            parse_result = PartialObjectParser._try_parse_key_value_pair(tokens, index)

            if parse_result is None:
                index += 1
                continue

            key, value, new_index = parse_result
            result[key] = value
            index = new_index

        return result if result else None

    @staticmethod
    def _try_parse_key_value_pair(tokens: List[CborToken], index: int) -> Optional[tuple]:
        """Try to parse a key-value pair starting at given index."""
        # Validate initial conditions
        key_result = PartialObjectParser._extract_key_at_index(tokens, index)
        if key_result is None:
            return None

        key, colon_index = key_result

        # Parse value after colon
        value_result = PartialObjectParser._parse_value_at_index(tokens, colon_index + 1)
        if value_result is None:
            return None

        value, new_index = value_result

        # Skip comma if present
        if PartialObjectParser._has_comma_at_index(tokens, new_index):
            new_index += 1

        return key, value, new_index

    @staticmethod
    def _extract_key_at_index(tokens: List[CborToken], index: int) -> Optional[tuple]:
        """Extract key and return colon index."""
        if index >= len(tokens):
            return None

        token = tokens[index]
        if token.major_type != 3:  # Not a string token
            return None

        key = token.value
        colon_index = index + 1

        # Look for colon separator
        if not PartialObjectParser._has_colon_at_index(tokens, colon_index):
            return None

        return key, colon_index

    @staticmethod
    def _has_colon_at_index(tokens: List[CborToken], index: int) -> bool:
        """Check if there's a colon at given index."""
        return index < len(tokens) and tokens[index].value == ':'

    @staticmethod
    def _has_comma_at_index(tokens: List[CborToken], index: int) -> bool:
        """Check if there's a comma at given index."""
        return index < len(tokens) and tokens[index].value == ','

    @staticmethod
    def _parse_value_at_index(tokens: List[CborToken], index: int) -> Optional[tuple]:
        """Parse value at given index."""
        if index >= len(tokens):
            return None

        value_token = tokens[index]

        if value_token.value == '{':
            # Nested partial object
            nested = PartialObjectParser.parse_partial_object(tokens[index:]) or {}
            return nested, index + 1
        else:
            return value_token.value, index + 1


class CborProcessor:
    """Processes CBOR-style tokens into JSON objects with partial support."""

    @staticmethod
    def process(tokens: List[CborToken]) -> Dict[str, Any]:
        """Process tokens into complete JSON objects."""
        result: Dict[str, Any] = {}
        map_starts = MapTokenProcessor.find_map_starts(tokens)

        for start in map_starts:
            processed_object = CborProcessor._process_single_map(tokens, start)
            if processed_object:
                result.update(processed_object)

        return result

    @staticmethod
    def _process_single_map(tokens: List[CborToken], start: int) -> Optional[Dict[str, Any]]:
        """Process a single map starting at given position."""
        end = MapTokenProcessor.find_map_end(tokens, start)

        if end >= start:
            # Complete map
            segment = tokens[start:end + 1]
            return CborProcessor._parse_complete_segment(segment)
        else:
            # Partial map
            segment = tokens[start:]
            return PartialObjectParser.parse_partial_object(segment)

    @staticmethod
    def _parse_complete_segment(segment: List[CborToken]) -> Optional[Dict[str, Any]]:
        """Parse a complete token segment."""
        json_string = JsonStringBuilder.build_json_string(segment)
        repaired_json = JsonStringBuilder.repair_json_string(json_string)

        try:
            obj = json.loads(repaired_json)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return PartialObjectParser.parse_partial_object(segment)


class StreamingJsonParser:
    """CBOR-inspired streaming JSON parser supporting partial fragments."""

    def __init__(self, tokenizer: CborTokenizer = None, processor: CborProcessor = None):
        """Initialize with dependency injection for loose coupling."""
        self._buffer: str = ''
        self._data: Dict[str, Any] = {}
        self._tokenizer = tokenizer or CborTokenizer()
        self._processor = processor or CborProcessor()

    def consume(self, buffer: str) -> None:
        """
        Consume a JSON text chunk and update parsed data, including partial values.

        Args:
            buffer: String chunk of JSON data to process
        """
        self._buffer += buffer
        tokens = self._tokenizer.tokenize(self._buffer)
        pairs = self._processor.process(tokens)
        self._data.update(pairs)

    def get(self) -> Dict[str, Any]:
        """
        Return all parsed key-value pairs, complete or partial.

        Returns:
            Dictionary containing all parsed key-value pairs
        """
        return dict(self._data)
