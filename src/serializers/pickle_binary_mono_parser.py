"""
Single-threaded Pickle Binary streaming parser implementation.
Note: Pickle is for Python objects, so this implements JSON parsing
with Pickle-inspired single-threaded buffering and object reconstruction.
"""
import json
from typing import Any, Dict, Optional, Tuple


class PairExtractor:
    """Extracts complete key-value pairs from objects."""

    def extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        return {
            key: value
            for key, value in obj.items()
            if self._is_valid_key(key)
        }

    def _is_valid_key(self, key: str) -> bool:
        """Check if key is valid and complete."""
        return isinstance(key, str) and len(key) > 0


class CharacterProcessor:
    """Pure functions for character processing."""

    @staticmethod
    def is_escape_char(char: str) -> bool:
        """Check if character is an escape character."""
        return char == '\\'

    @staticmethod
    def is_quote_char(char: str) -> bool:
        """Check if character is a quote."""
        return char == '"'

    @staticmethod
    def is_open_brace(char: str) -> bool:
        """Check if character is an opening brace."""
        return char == '{'

    @staticmethod
    def is_close_brace(char: str) -> bool:
        """Check if character is a closing brace."""
        return char == '}'


class StringState:
    """Immutable state for string parsing."""

    def __init__(self, in_string: bool = False, escape_next: bool = False):
        self.in_string = in_string
        self.escape_next = escape_next

    def process_char(self, char: str) -> 'StringState':
        """Process character and return new state."""
        if self.escape_next:
            return StringState(self.in_string, False)

        if CharacterProcessor.is_escape_char(char):
            return StringState(self.in_string, True)

        if CharacterProcessor.is_quote_char(char):
            return StringState(not self.in_string, False)

        return StringState(self.in_string, False)


class BraceCounter:
    """Pure functions for brace counting."""

    @staticmethod
    def update_count(char: str, current_count: int, in_string: bool) -> int:
        """Update brace count based on character."""
        if in_string:
            return current_count

        if CharacterProcessor.is_open_brace(char):
            return current_count + 1
        elif CharacterProcessor.is_close_brace(char):
            return current_count - 1

        return current_count

    @staticmethod
    def is_balanced(count: int) -> bool:
        """Check if braces are balanced."""
        return count == 0


class ObjectEndFinder:
    """Finds the end position of complete JSON objects."""

    def find_object_end(self, json_str: str) -> int:
        """Find the end position of a complete JSON object."""
        brace_count = 0
        string_state = StringState()

        for i, char in enumerate(json_str):
            string_state = string_state.process_char(char)
            brace_count = BraceCounter.update_count(char, brace_count, string_state.in_string)

            if BraceCounter.is_balanced(brace_count) and brace_count == 0 and i > 0:
                return i

        return -1


class StringEndFinder:
    """Finds the end position of strings."""

    def find_string_end(self, json_str: str) -> int:
        """Find the end position of a string."""
        if not self._starts_with_quote(json_str):
            return -1

        return self._find_closing_quote(json_str)

    def _starts_with_quote(self, json_str: str) -> bool:
        """Check if string starts with quote."""
        return json_str.startswith('"')

    def _find_closing_quote(self, json_str: str) -> int:
        """Find the closing quote position."""
        escape_next = False

        for i in range(1, len(json_str)):
            char = json_str[i]

            if escape_next:
                escape_next = False
                continue

            if CharacterProcessor.is_escape_char(char):
                escape_next = True
                continue

            if CharacterProcessor.is_quote_char(char):
                return i

        return -1


class JsonValidator:
    """Pure functions for JSON validation."""

    @staticmethod
    def is_valid_dict(obj: Any) -> bool:
        """Check if object is a valid dictionary."""
        return isinstance(obj, dict)

    @staticmethod
    def has_content(data: Dict[str, Any]) -> bool:
        """Check if dictionary has content."""
        return bool(data)


class BraceBalancer:
    """Pure functions for brace balancing."""

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


class PartialParser:
    """Handles partial JSON parsing."""

    def __init__(self, pair_extractor: PairExtractor):
        self._pair_extractor = pair_extractor

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

    def _balance_braces(self, test_str: str) -> Optional[str]:
        """Balance braces in a JSON string."""
        open_count, close_count = BraceBalancer.count_braces(test_str)

        if BraceBalancer.needs_balancing(open_count, close_count):
            return BraceBalancer.balance_string(test_str, open_count, close_count)

        return None

    def _try_parse_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        """Try to parse JSON string."""
        try:
            obj = json.loads(json_str)
            return obj if JsonValidator.is_valid_dict(obj) else None
        except json.JSONDecodeError:
            return None


class ObjectHandler:
    """Handles JSON object processing."""

    def __init__(self, object_finder: ObjectEndFinder, pair_extractor: PairExtractor):
        self._object_finder = object_finder
        self._pair_extractor = pair_extractor

    def handle_object_start(self, buffer: str, position: int) -> Dict[str, Any]:
        """Handle the start of JSON object."""
        try:
            remaining = buffer[position:]
            obj_end = self._object_finder.find_object_end(remaining)

            if obj_end > 0:
                return self._parse_complete_object(remaining, obj_end)

        except ValueError:
            pass

        return {}

    def _parse_complete_object(self, remaining: str, obj_end: int) -> Dict[str, Any]:
        """Parse a complete JSON object."""
        json_str = remaining[:obj_end + 1]
        obj = json.loads(json_str)

        if JsonValidator.is_valid_dict(obj):
            return self._pair_extractor.extract_complete_pairs(obj)

        return {}


class StringHandler:
    """Handles string processing."""

    def __init__(self, string_finder: StringEndFinder):
        self._string_finder = string_finder

    def handle_string_start(self, buffer: str, position: int) -> bool:
        """Handle the start of string value."""
        try:
            remaining = buffer[position:]
            string_end = self._string_finder.find_string_end(remaining)
            return string_end > 0
        except (IndexError, AttributeError, TypeError):
            return False


class CharacterHandler:
    """Handles individual character processing."""

    def __init__(self, object_handler: ObjectHandler, string_handler: StringHandler):
        self._object_handler = object_handler
        self._string_handler = string_handler

    def handle_open_brace(self, buffer: str, position: int) -> Dict[str, Any]:
        """Handle opening brace character."""
        return self._object_handler.handle_object_start(buffer, position)

    def handle_quote(self, buffer: str, position: int) -> None:
        """Handle quote character."""
        self._string_handler.handle_string_start(buffer, position)


class DepthTracker:
    """Tracks parsing depth."""

    def __init__(self):
        self._current_depth = 0

    def increment(self) -> None:
        """Increment depth."""
        self._current_depth += 1

    def decrement(self) -> None:
        """Decrement depth if positive."""
        if self._current_depth > 0:
            self._current_depth -= 1

    def get_depth(self) -> int:
        """Get current depth."""
        return self._current_depth


class SingleThreadedProcessor:
    """Single-threaded processor for Pickle-inspired parsing."""

    def __init__(self, object_handler: ObjectHandler, string_handler: StringHandler,
                 partial_parser: PartialParser):
        self._char_handler = CharacterHandler(object_handler, string_handler)
        self._partial_parser = partial_parser
        self._depth_tracker = DepthTracker()

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
        if CharacterProcessor.is_open_brace(char):
            return self._handle_open_brace(buffer, position)
        elif CharacterProcessor.is_close_brace(char):
            self._handle_close_brace()
        elif CharacterProcessor.is_quote_char(char):
            self._handle_quote(buffer, position)

        return {}

    def _handle_open_brace(self, buffer: str, position: int) -> Dict[str, Any]:
        """Handle opening brace with fallback."""
        new_data = self._char_handler.handle_open_brace(buffer, position)

        if not JsonValidator.has_content(new_data):
            new_data = self._partial_parser.try_partial_parse(buffer, position)

        self._depth_tracker.increment()
        return new_data

    def _handle_close_brace(self) -> None:
        """Handle closing brace."""
        self._depth_tracker.decrement()

    def _handle_quote(self, buffer: str, position: int) -> None:
        """Handle quote character."""
        self._char_handler.handle_quote(buffer, position)


class StreamingJsonParser:
    """Single-threaded streaming JSON parser with Pickle-inspired object handling."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._buffer = ""
        self._parsed_data = {}
        self._processor = self._create_processor()

    def _create_processor(self) -> SingleThreadedProcessor:
        """Create and configure the processor."""
        pair_extractor = PairExtractor()
        object_finder = ObjectEndFinder()
        string_finder = StringEndFinder()
        partial_parser = PartialParser(pair_extractor)
        object_handler = ObjectHandler(object_finder, pair_extractor)
        string_handler = StringHandler(string_finder)

        return SingleThreadedProcessor(object_handler, string_handler, partial_parser)

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally.

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
        return self._parsed_data.copy()