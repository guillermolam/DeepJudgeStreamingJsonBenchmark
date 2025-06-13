"""
ReactiveX Streaming parser implementation.
Uses reactive programming patterns for streaming JSON parsing.
"""
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable, List


@dataclass
class StreamEvent:
    """Represents an event in the reactive stream."""
    event_type: str
    data: Any
    timestamp: float


class PairExtractor:
    """Extracts complete key-value pairs from objects."""

    def extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        complete_pairs = {}

        for key, value in obj.items():
            if self._is_valid_key(key):
                complete_pairs[key] = value

        return complete_pairs

    @staticmethod
    def _is_valid_key(key: str) -> bool:
        """Check if the key is valid and complete."""
        return isinstance(key, str) and len(key) > 0


class JsonChunkTransformer:
    """Transforms buffer into potential JSON chunks."""

    # ---------- public API -------------------------------------------------
    def transform_to_json_chunks(self, buffer: str) -> List[str]:
        """Split an incoming buffer into complete JSON-object chunks."""
        chunks: List[str] = []
        current: List[str] = []
        state = self._init_state()

        for ch in buffer:
            current.append(ch)

            if self._skip_due_to_escape(state, ch):
                continue

            self._toggle_string_state(state, ch)

            if not state["in_string"]:
                brace_changed = self._update_brace_count(state, ch)
                if brace_changed and self._is_complete(state, current):
                    chunks.append("".join(current).strip())
                    current.clear()

        return chunks

    # ---------- helper functions ------------------------------------------
    @staticmethod
    def _init_state() -> Dict[str, Any]:
        """Initialise parsing state."""
        return {"brace": 0, "in_string": False, "escape_next": False}

    @staticmethod
    def _skip_due_to_escape(state: Dict[str, Any], ch: str) -> bool:
        """Handle back-slash escape logic."""
        if state["escape_next"]:
            state["escape_next"] = False
            return True
        if ch == "\\":
            state["escape_next"] = True
            return True
        return False

    @staticmethod
    def _toggle_string_state(state: Dict[str, Any], ch: str) -> None:
        """Flip the *inside-string* flag when an unescaped quote is met."""
        if ch == '"' and not state["escape_next"]:
            state["in_string"] = not state["in_string"]

    @staticmethod
    def _update_brace_count(state: Dict[str, Any], ch: str) -> bool:
        """Adjust brace counter, return *True* when it changed."""
        if ch == "{":
            state["brace"] += 1
            return True
        if ch == "}":
            state["brace"] -= 1
            return True
        return False

    @staticmethod
    def _is_complete(state: Dict[str, Any], cur: List[str]) -> bool:
        """An object is complete when the brace counter hits zero."""
        return state["brace"] == 0 and "".join(cur).strip()


class PartialChunkParser:
    """Parses partial JSON chunks."""

    def __init__(self, pair_extractor: PairExtractor):
        self._pair_extractor = pair_extractor

    def parse_partial_chunk(self, chunk: str) -> Optional[Dict[str, Any]]:
        """Parse partial JSON chunk reactively."""
        if not isinstance(chunk, str) or not chunk.strip():
            return None

        if '{' not in chunk:
            return None

        # Find the start of JSON
        start_pos = chunk.find('{')
        json_part = chunk[start_pos:]

        try:
            # Try to balance braces
            balanced_json = self._balance_braces(json_part)
            if not balanced_json:
                return None

            obj = self._try_parse_json(balanced_json)
            if not obj:
                return None

            return self._pair_extractor.extract_complete_pairs(obj)
        except ValueError:
            return None

    @staticmethod
    def _balance_braces(json_part: str) -> Optional[str]:
        """Balance braces in JSON string."""
        open_braces = json_part.count('{')
        close_braces = json_part.count('}')

        if open_braces > close_braces:
            return json_part + '}' * (open_braces - close_braces)

        return None

    @staticmethod
    def _try_parse_json(json_str: str) -> Optional[Dict[str, Any]]:
        """Try to parse JSON string."""
        try:
            obj = json.loads(json_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None


class ParsedObjectTransformer:
    """Transforms JSON chunks into parsed objects."""

    def __init__(self, pair_extractor: PairExtractor, partial_parser: PartialChunkParser):
        self._pair_extractor = pair_extractor
        self._partial_parser = partial_parser

    def transform_to_parsed_objects(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """Transform JSON chunks into parsed objects."""
        parsed_objects = []

        for chunk in chunks:
            parsed_obj = self._process_chunk(chunk)
            if parsed_obj:
                parsed_objects.append(parsed_obj)

        return parsed_objects

    def _process_chunk(self, chunk: str) -> Optional[Dict[str, Any]]:
        """Process a single chunk."""
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                complete_pairs = self._pair_extractor.extract_complete_pairs(obj)
                return complete_pairs if complete_pairs else None
        except json.JSONDecodeError:
            # Try partial parsing with more specific exception handling
            return self._partial_parser.parse_partial_chunk(chunk)

        return None


class ObserverManager:
    """Manages observers for the reactive stream."""

    def __init__(self):
        self._observers = []

    def subscribe(self, observer: Callable[[str, Any], None]) -> None:
        """Subscribe an observer to the reactive stream."""
        self._observers.append(observer)

    def notify_observers(self, event_type: str, data: Any) -> None:
        """Notify all observers of an event."""
        for observer in self._observers:
            try:
                observer(event_type, data)
            except ValueError:
                continue  # Don't let observer errors break the stream


class StreamDataManager:
    """Manages stream data_gen and events."""

    def __init__(self):
        self._data_stream = []
        self._subject_lock = threading.Lock()

    def add_event(self, event_type: str, data: Any) -> None:
        """Add event to data_gen stream."""
        with self._subject_lock:
            self._data_stream.append(StreamEvent(
                event_type=event_type,
                data=data,
                timestamp=time.time()
            ))

    def get_stream_copy(self) -> List[StreamEvent]:
        """Get a thread-safe copy of data_gen stream."""
        with self._subject_lock:
            return self._data_stream.copy()


class ParsedDataManager:
    """Thread-safe management of parsed data_gen."""

    def __init__(self):
        self._parsed_data = {}
        self._data_lock = threading.Lock()

    def update_data(self, new_data: Dict[str, Any]) -> None:
        """Thread-safe data_gen update."""
        with self._data_lock:
            self._parsed_data.update(new_data)

    def get_data_copy(self) -> Dict[str, Any]:
        """Get a thread-safe copy of parsed data_gen."""
        with self._data_lock:
            return self._parsed_data.copy()


class ReactiveStreamProcessor:
    """Main reactive stream processor."""

    def __init__(self, chunk_transformer: JsonChunkTransformer,
                 object_transformer: ParsedObjectTransformer,
                 observer_manager: ObserverManager,
                 stream_manager: StreamDataManager,
                 data_manager: ParsedDataManager):
        self._chunk_transformer = chunk_transformer
        self._object_transformer = object_transformer
        self._observer_manager = observer_manager
        self._stream_manager = stream_manager
        self._data_manager = data_manager

    def emit_buffer_change(self, new_data: str) -> None:
        """Emit buffer change event to observers."""
        self._stream_manager.add_event('buffer_change', new_data)
        self._observer_manager.notify_observers('buffer_change', new_data)

    def process_reactive_stream(self, buffer: str) -> None:
        """Process the data_gen stream using reactive patterns."""
        # Transform stream: buffer -> JSON chunks -> parsed objects
        json_chunks = self._chunk_transformer.transform_to_json_chunks(buffer)
        parsed_objects = self._object_transformer.transform_to_parsed_objects(json_chunks)

        # Subscribe to parsed objects
        self._subscribe_to_parsed_objects(parsed_objects)

    def _subscribe_to_parsed_objects(self, parsed_objects: List[Dict[str, Any]]) -> None:
        """Subscribe to parsed objects and update state."""
        for obj in parsed_objects:
            self._on_next_parsed_object(obj)

    def _on_next_parsed_object(self, obj: Dict[str, Any]) -> None:
        """Handle the next parsed object in reactive stream."""
        self._data_manager.update_data(obj)

        # Emit parsed object event
        self._observer_manager.notify_observers('parsed_object', obj)

    def subscribe_observer(self, observer: Callable[[str, Any], None]) -> None:
        """Subscribe an observer to the reactive stream."""
        self._observer_manager.subscribe(observer)

    def get_parsed_data(self) -> Dict[str, Any]:
        """Get current parsed data_gen."""
        return self._data_manager.get_data_copy()


class StreamingJsonParser:
    """ReactiveX-inspired streaming JSON parser with observable patterns."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._buffer = ""

        # Initialize components
        self._pair_extractor = PairExtractor()
        self._chunk_transformer = JsonChunkTransformer()
        self._partial_parser = PartialChunkParser(self._pair_extractor)
        self._object_transformer = ParsedObjectTransformer(self._pair_extractor, self._partial_parser)
        self._observer_manager = ObserverManager()
        self._stream_manager = StreamDataManager()
        self._data_manager = ParsedDataManager()

        # Initialize main processor
        self._processor = ReactiveStreamProcessor(
            self._chunk_transformer,
            self._object_transformer,
            self._observer_manager,
            self._stream_manager,
            self._data_manager
        )

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data_gen incrementally using reactive patterns.

        Args:
            buffer: String chunk of JSON data_gen to process
        """
        self._buffer += buffer

        # Emit buffer change event
        self._processor.emit_buffer_change(buffer)

        # Process reactively
        self._processor.process_reactive_stream(self._buffer)

    def subscribe(self, observer: Callable[[str, Any], None]) -> None:
        """Subscribe an observer to the reactive stream."""
        self._processor.subscribe_observer(observer)

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self._processor.get_parsed_data()
