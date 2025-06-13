"""
Standard JSON library streaming parser implementation.
Uses json.JSONDecoder with raw_decode for incremental parsing.
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, NamedTuple


# Immutable data_gen structures for better state management
@dataclass(frozen=True)
class ParseResult:
    """Immutable container for parsing results."""
    parsed_data: Dict[str, Any]
    new_position: int


@dataclass(frozen=True)
class BraceTrackingResult:
    """Immutable result of brace tracking operation."""
    found: bool
    end_position: int = -1


class CharacterState(NamedTuple):
    """Immutable state for character processing."""
    brace_count: int
    in_string: bool
    escape_next: bool


# Protocols for dependency inversion
class JsonDecoder(Protocol):
    """Protocol for JSON decoder abstraction."""

    def raw_decode(self, s: str, idx: int = 0) -> tuple[Any, int]: ...


class ObjectExtractor(Protocol):
    """Protocol for object extraction abstraction."""

    def extract_partial_objects(self, buffer: str, position: int) -> ParseResult: ...


class PairFilter(Protocol):
    """Protocol for pair filtering abstraction."""

    def filter_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]: ...


class BraceTracker(Protocol):
    """Protocol for brace tracking abstraction."""

    def find_complete_object(self, text: str, start_position: int) -> BraceTrackingResult: ...


# Main parser class following Single Responsibility Principle
class StreamingJsonParser:
    """
    Streaming JSON parser using a standard library with incremental decoding.

    Single Responsibility: Coordinates parsing workflow only.
    """

    def __init__(self,
                 decoder: Optional[JsonDecoder] = None,
                 extractor: Optional[ObjectExtractor] = None,
                 pair_filter: Optional[PairFilter] = None):
        """Initialize with dependency injection for testability."""
        self._state = self._create_initial_state()
        self._components = self._create_components(decoder, extractor, pair_filter)

    @staticmethod
    def _create_initial_state() -> Dict[str, Any]:
        """Pure function: Create initial parser state."""
        return {
            'buffer': '',
            'parsed_data': {},
            'current_position': 0
        }

    @staticmethod
    def _create_components(decoder: Optional[JsonDecoder],
                           extractor: Optional[ObjectExtractor],
                           pair_filter: Optional[PairFilter]) -> Dict[str, Any]:
        """Pure function: Create parser components with defaults."""
        return {
            'decoder': decoder or json.JSONDecoder(),
            'extractor': extractor or PartialObjectExtractor(),
            'pair_filter': pair_filter or CompletePairFilter()
        }

    def consume(self, buffer: str) -> None:
        """Process a chunk of JSON data_gen incrementally."""
        self._state = self._append_to_buffer(self._state, buffer)
        self._state = self._parse_and_update_state(self._state)

    @staticmethod
    def _append_to_buffer(state: Dict[str, Any], buffer: str) -> Dict[str, Any]:
        """Pure function: Append buffer to state."""
        return {**state, 'buffer': state['buffer'] + buffer}

    def _parse_and_update_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Parse buffer and return updated state."""
        parser = IncrementalParser(
            self._components['decoder'],
            self._components['extractor'],
            self._components['pair_filter']
        )

        result = parser.parse(state['buffer'], state['current_position'])

        return {
            **state,
            'parsed_data': {**state['parsed_data'], **result.parsed_data},
            'current_position': result.new_position
        }

    def get(self) -> Dict[str, Any]:
        """Return current parsed state as a Python object."""
        return self._state['parsed_data'].copy()


# Parser strategy following Strategy Pattern
class IncrementalParser:
    """
    Handles incremental parsing logic.

    Single Responsibility: Parse buffer incrementally.
    Open/Closed: Extensible through component injection.
    """

    def __init__(self, decoder: JsonDecoder, extractor: ObjectExtractor, pair_filter: PairFilter):
        self._decoder = decoder
        self._extractor = extractor
        self._filter = pair_filter

    def parse(self, buffer: str, current_position: int) -> ParseResult:
        """Parse buffer incrementally from the current position."""
        if not self._is_valid_input(buffer, current_position):
            return ParseResult({}, current_position)

        return self._parse_buffer_from_position(buffer, current_position)

    @staticmethod
    def _is_valid_input(buffer: str, position: int) -> bool:
        """Pure function: Validate input parameters."""
        return isinstance(buffer, str) and isinstance(position, int) and position >= 0

    def _parse_buffer_from_position(self, buffer: str, position: int) -> ParseResult:
        """Parse buffer starting from given position."""
        parsed_data = {}
        current_pos = position

        while current_pos < len(buffer):
            parse_attempt = self._try_decode_at_position(buffer, current_pos)

            if parse_attempt.success:
                parsed_data.update(parse_attempt.data)
                current_pos = parse_attempt.new_position
            else:
                # Fallback to partial extraction
                extraction_result = self._extractor.extract_partial_objects(buffer, current_pos)
                parsed_data.update(extraction_result.parsed_data)
                current_pos = extraction_result.new_position
                break

        return ParseResult(parsed_data, current_pos)

    def _try_decode_at_position(self, buffer: str, position: int) -> 'DecodeAttempt':
        """Try to decode JSON at specific position."""
        try:
            obj, idx = self._decoder.raw_decode(buffer, position)

            if isinstance(obj, dict):
                complete_pairs = self._filter.filter_complete_pairs(obj)
                return DecodeAttempt(True, complete_pairs, position + idx)

            return DecodeAttempt(True, {}, position + idx)

        except json.JSONDecodeError:
            return DecodeAttempt(False, {}, position)


@dataclass(frozen=True)
class DecodeAttempt:
    """Immutable result of decode attempt."""
    success: bool
    data: Dict[str, Any]
    new_position: int


# Object extraction following Single Responsibility
class PartialObjectExtractor:
    """
    Extracts partial but valid key-value pairs from incomplete JSON.

    Single Responsibility: Extract partial objects only.
    """

    def __init__(self, brace_tracker: Optional[BraceTracker] = None):
        self._brace_tracker = brace_tracker or OptimizedBraceTracker()

    def extract_partial_objects(self, buffer: str, current_position: int) -> ParseResult:
        """Extract partial but valid key-value pairs from incomplete JSON."""
        if not self._is_valid_extraction_input(buffer, current_position):
            return ParseResult({}, current_position)

        remaining_buffer = buffer[current_position:]
        brace_position = self._find_opening_brace(remaining_buffer)

        if brace_position == -1:
            return ParseResult({}, current_position)

        return self._extract_from_brace_position(
            remaining_buffer, brace_position, current_position
        )

    @staticmethod
    def _is_valid_extraction_input(buffer: str, position: int) -> bool:
        """Pure function: Validate extraction input."""
        return isinstance(buffer, str) and isinstance(position, int) and position >= 0

    @staticmethod
    def _find_opening_brace(text: str) -> int:
        """Pure function: Find opening brace position."""
        return text.find('{')

    def _extract_from_brace_position(self,
                                     remaining_buffer: str,
                                     brace_position: int,
                                     current_position: int) -> ParseResult:
        """Extract object starting from brace position."""
        tracking_result = self._brace_tracker.find_complete_object(
            remaining_buffer, brace_position
        )

        if not tracking_result.found:
            return ParseResult({}, current_position)

        return self._parse_tracked_object(
            remaining_buffer, tracking_result, current_position
        )

    @staticmethod
    def _parse_tracked_object(remaining_buffer: str,
                              tracking_result: BraceTrackingResult,
                              current_position: int) -> ParseResult:
        """Parse object found by brace tracker."""
        try:
            partial_json = remaining_buffer[:tracking_result.end_position + 1]
            obj = json.loads(partial_json)

            if isinstance(obj, dict):
                filter_obj = CompletePairFilter()
                complete_pairs = filter_obj.filter_complete_pairs(obj)
                new_position = current_position + tracking_result.end_position + 1
                return ParseResult(complete_pairs, new_position)

        except json.JSONDecodeError:
            pass

        return ParseResult({}, current_position)


# Optimized brace tracker with character handlers
class OptimizedBraceTracker:
    """
    Optimized brace tracker using character state machine.

    Single Responsibility: Track brace balance efficiently.
    """

    def find_complete_object(self, text: str, start_position: int) -> BraceTrackingResult:
        """Find a complete object by tracking brace balance."""
        if not self._is_valid_tracking_input(text, start_position):
            return BraceTrackingResult(False)

        state = CharacterState(brace_count=0, in_string=False, escape_next=False)

        for position, char in enumerate(text[start_position:], start_position):
            state = self._process_character(char, state)

            if self._is_object_complete(state):
                return BraceTrackingResult(True, position)

        return BraceTrackingResult(False)

    @staticmethod
    def _is_valid_tracking_input(text: str, start_position: int) -> bool:
        """Pure function: Validate tracking input."""
        return (isinstance(text, str) and
                isinstance(start_position, int) and
                0 <= start_position < len(text))

    def _process_character(self, char: str, state: CharacterState) -> CharacterState:
        """Pure function: Process character and return new state."""
        if state.escape_next:
            return state._replace(escape_next=False)

        if char == '\\':
            return state._replace(escape_next=True)

        if char == '"':
            return state._replace(in_string=not state.in_string)

        if not state.in_string:
            return self._process_structural_character(char, state)

        return state

    @staticmethod
    def _process_structural_character(char: str, state: CharacterState) -> CharacterState:
        """Pure function: Process structural characters."""
        if char == '{':
            return state._replace(brace_count=state.brace_count + 1)
        elif char == '}':
            return state._replace(brace_count=state.brace_count - 1)
        return state

    @staticmethod
    def _is_object_complete(state: CharacterState) -> bool:
        """Pure function: Check if object parsing is complete."""
        return not state.in_string and state.brace_count == 0


# Value filter following Single Responsibility
class CompletePairFilter:
    """
    Filters complete key-value pairs.

    Single Responsibility: Filter valid pairs only.
    """

    def filter_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out incomplete key-value pairs, allowing partial string values."""
        if not isinstance(obj, dict):
            return {}

        return {
            key: value
            for key, value in obj.items()
            if self._is_valid_value(value)
        }

    @staticmethod
    def _is_valid_value(value: Any) -> bool:
        """Pure function: Check if value is valid for inclusion."""
        return isinstance(value, (str, int, float, bool, list, dict)) or value is None


# Factory for creating parser instances
class StreamingJsonParserFactory:
    """
    Factory for creating parser instances.

    Single Responsibility: Create configured parser instances.
    """

    @staticmethod
    def create_default() -> StreamingJsonParser:
        """Create parser with default components."""
        return StreamingJsonParser()

    @staticmethod
    def create_with_custom_tracker(tracker: BraceTracker) -> StreamingJsonParser:
        """Create parser with custom brace tracker."""
        extractor = PartialObjectExtractor(tracker)
        return StreamingJsonParser(extractor=extractor)

    @staticmethod
    def create_optimized() -> StreamingJsonParser:
        """Create optimized parser instance."""
        tracker = OptimizedBraceTracker()
        extractor = PartialObjectExtractor(tracker)
        pair_filter = CompletePairFilter()

        return StreamingJsonParser(
            extractor=extractor,
            pair_filter=pair_filter
        )
