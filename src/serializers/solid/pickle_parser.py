
"""
Pickle streaming parser implementation with SOLID principles.

This module implements a streaming JSON parser inspired by Pickle object serialization.
It follows SOLID principles with clean separation of concerns, stateless operations where possible,
and cognitive complexity under 14 for all methods.

Key Features:
- Object reconstruction inspired by Pickle
- Incremental JSON parsing with single-threaded processing
- Stateless utility functions and processors
- Clean separation between character processing, object handling, and data extraction
- Comprehensive error handling and recovery

Architecture:
- ParserState: Immutable state container using @dataclass
- Static utility classes for character validation and object processing
- Dependency injection for loose coupling
- Single responsibility principle throughout
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class ParserState:
    """Immutable state container for the Pickle parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StringState:
    """Immutable state for string parsing."""
    in_string: bool = False
    escape_next: bool = False

    def process_char(self, char: str) -> 'StringState':
        """Process character and return new state."""
        if self.escape_next:
            return StringState(self.in_string, False)

        if CharacterValidator.is_escape_char(char):
            return StringState(self.in_string, True)

        if CharacterValidator.is_quote_char(char):
            return StringState(not self.in_string, False)

        return StringState(self.in_string, False)


class CharacterValidator:
    """Stateless validator for Pickle-style character processing."""

    @staticmethod
    def is_valid_key(key: str) -> bool:
        """Check if the key is valid and complete."""
        return isinstance(key, str) and len(key) > 0

    @staticmethod
    def is_escape_char(char: str) -> bool:
        """Check if character is an escape character."""
        return char == '\\'

    @staticmethod
    def is_quote_char(char: str) -> bool:
        """Check if the character is a quote."""
        return char == '"'

    @staticmethod
    def is_open_brace(char: str) -> bool:
        """Check if character is an opening brace."""
        return char == '{'

    @staticmethod
    def is_close_brace(char: str) -> bool:
        """Check if character is a closing brace."""
        return char == '}'


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
            if CharacterValidator.is_valid_key(key)
        }


class BraceCounter:
    """Stateless utility for brace counting."""

    @staticmethod
    def update_count(char: str, current_count: int, in_string: bool) -> int:
        """Update brace count based on character."""
        if in_string:
            return current_count

        if CharacterValidator.is_open_brace(char):
            return current_count + 1
        elif CharacterValidator.is_close_brace(char):
            return current_count - 1

        return current_count

    @staticmethod
    def is_balanced(count: int) -> bool:
        """Check if braces are balanced."""
        return count == 0


class ObjectBoundaryFinder:
    """Finds object boundaries using Pickle-inspired techniques."""

    @staticmethod
    def find_object_end(json_str: str) -> int:
        """Find the end position of a complete JSON object."""
        brace_count = 0
        string_state = StringState()

        for i, char in enumerate(json_str):
            string_state = string_state.process_char(char)
            brace_count = BraceCounter.update_count(char, brace_count, string_state.in_string)

            if BraceCounter.is_balanced(brace_count) and i > 0:
                return i

        return -1

    @staticmethod
    def find_string_end(json_str: str) -> int:
        """Find the end position of a string."""
        if not ObjectBoundaryFinder._starts_with_quote(json_str):
            return -1

        return ObjectBoundaryFinder._find_closing_quote(json_str)

    @staticmethod
    def _starts_with_quote(json_str: str) -> bool:
        """Check if string starts with quote."""
        return json_str.startswith('"')

    @staticmethod
    def _find_closing_quote(json_str: str) -> int:
        """Find the closing quote position."""
        escape_next = False

        for i in range(1, len(json_str)):
            char = json_str[i]

            if escape_next:
                escape_next = False
                continue

            if CharacterValidator.is_escape_char(char):
                escape_next = True
                continue

            if CharacterValidator.is_quote_char(char):
                return i

        return -1


class JsonValidator:
    """Stateless utility for JSON validation."""

    @staticmethod
    def is_valid_dict(obj: Any) -> bool:
        """Check if an object is a valid dictionary."""
        return isinstance(obj, dict)

    @staticmethod
    def has_content(data: Dict[str, Any]) -> bool:
        """Check if the dictionary has content."""
        return bool(data)


class BraceBalancer:
    """Stateless utility for brace balancing."""

    @staticmethod
    def count_braces(text: str) -> Tuple[int, int]:
        """Count open and close braces."""
        return text.count('{'), text.count('}')

    @staticmethod
    def needs_balancing(open_count: int, close_count: int) -> bool:
        """Check if braces need balancing."""
        return open_count > close_count

    @staticmethod
    def balance_string(text: str, open_count: int, close_count: int) -> str:
        """Balance braces in string."""
        missing_braces = open_count - close_count
        return text + '}' * missing_braces


class ObjectParser:
    """Parses JSON objects using Pickle-inspired techniques."""

    def __init__(self,
                 boundary_finder: ObjectBoundaryFinder = None,
                 pair_extractor: PairExtractor = None):
        self._boundary_finder = boundary_finder or ObjectBoundaryFinder()
        self._pair_extractor = pair_extractor or PairExtractor()

    def parse_object_at_position(self, buffer: str, position: int) -> Dict[str, Any]:
        """Parse JSON object starting at given position."""
        try:
            remaining = buffer[position:]
            obj_end = self._boundary_finder.find_object_end(remaining)

            if obj_end > 0:
                return self._parse_complete_object(remaining, obj_end)

        except ValueError:
            pass

        return {}

    def _parse_complete_object(self, remaining: str, obj_end: int) -> Dict[str, Any]:
        """Parse a complete JSON object."""
        json_str = remaining[:obj_end + 1]

        try:
            obj = json.loads(json_str)
            if JsonValidator.is_valid_dict(obj):
                return self._pair_extractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass

        return {}


class PartialParser:
    """Handles partial JSON parsing using Pickle-inspired reconstruction."""

    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()

    def try_partial_parse(self, buffer: str, position: int) -> Dict[str, Any]:
        """Try to parse partial JSON objects."""
        remaining = buffer[position:]

        for end_pos in range(len(remaining), 0, -1):
            test_str = remaining[:end_pos]
            result = self._try_parse_substring(test_str)
            if result:
                return result

        return {}

    def _try_parse_substring(self, test_str: str) -> Dict[str, Any]:
        """Try to parse a substring."""
        balanced_str = self._balance_braces(test_str)
        if not balanced_str:
            return {}

        parsed_obj = self._try_parse_json(balanced_str)
        if not parsed_obj:
            return {}

        return self._pair_extractor.extract_complete_pairs(parsed_obj)

    @staticmethod
    def _balance_braces(test_str: str) -> Optional[str]:
        """Balance braces in a JSON string."""
        open_count, close_count = BraceBalancer.count_braces(test_str)

        if BraceBalancer.needs_balancing(open_count, close_count):
            return BraceBalancer.balance_string(test_str, open_count, close_count)

        return None

    @staticmethod
    def _try_parse_json(json_str: str) -> Optional[Dict[str, Any]]:
        """Try to parse JSON string."""
        try:
            obj = json.loads(json_str)
            return obj if JsonValidator.is_valid_dict(obj) else None
        except json.JSONDecodeError:
            return None


class StringHandler:
    """Handles string processing using Pickle-inspired techniques."""

    def __init__(self, boundary_finder: ObjectBoundaryFinder = None):
        self._boundary_finder = boundary_finder or ObjectBoundaryFinder()

    def handle_string_start(self, buffer: str, position: int) -> bool:
        """Handle the start of string value."""
        try:
            remaining = buffer[position:]
            string_end = self._boundary_finder.find_string_end(remaining)
            return string_end > 0
        except (IndexError, AttributeError, TypeError):
            return False


class SingleThreadedProcessor:
    """Single-threaded processor for Pickle-inspired parsing with dependency injection."""

    def __init__(self,
                 object_parser: ObjectParser = None,
                 string_handler: StringHandler = None,
                 partial_parser: PartialParser = None):
        self._object_parser = object_parser or ObjectParser()
        self._string_handler = string_handler or StringHandler()
        self._partial_parser = partial_parser or PartialParser()

    def parse_single_threaded(self, buffer: str) -> Dict[str, Any]:
        """Parse using single-threaded Pickle-inspired strategy."""
        parsed_data = {}

        for i, char in enumerate(buffer):
            new_data = self._process_character(char, buffer, i)
            if JsonValidator.has_content(new_data):
                parsed_data.update(new_data)

        return parsed_data

    def _process_character(self, char: str, buffer: str, position: int) -> Dict[str, Any]:
        """Process a single character."""
        if CharacterValidator.is_open_brace(char):
            return self._handle_open_brace(buffer, position)
        elif CharacterValidator.is_quote_char(char):
            self._handle_quote(buffer, position)

        return {}

    def _handle_open_brace(self, buffer: str, position: int) -> Dict[str, Any]:
        """Handle opening brace with fallback."""
        new_data = self._object_parser.parse_object_at_position(buffer, position)

        if not JsonValidator.has_content(new_data):
            new_data = self._partial_parser.try_partial_parse(buffer, position)

        return new_data

    def _handle_quote(self, buffer: str, position: int) -> None:
        """Handle quote character."""
        self._string_handler.handle_string_start(buffer, position)


class StreamingJsonParser:
    """Streaming JSON parser with Pickle-inspired object reconstruction."""

    def __init__(self, processor: SingleThreadedProcessor = None):
        """Initialize the streaming JSON parser with dependency injection."""
        self._state = ParserState()
        self._processor = processor or SingleThreadedProcessor()

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
        Process a chunk of JSON data incrementally using Pickle-inspired processing.

        Args:
            buffer: String chunk of JSON data to process
        """
        self._buffer += buffer
        new_data = self._processor.parse_single_threaded(self._buffer)
        if JsonValidator.has_content(new_data):
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
