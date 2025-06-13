"""
Ultra-JSON (ujson) streaming parser implementation.
Uses ujson-inspired high-performance parsing techniques for streaming JSON.
"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Add src/ to sys.path so Python can find your packages
sys.path.insert(0, str(Path(__file__).parent / "src"))


@dataclass
class ParserState:
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    fast_buffer: bytearray = field(default_factory=bytearray)
    parse_position: int = 0


class StreamingJsonParser:
    """Streaming JSON parser with Ultra-JSON inspired high-performance techniques."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._state = ParserState()

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
    def fast_buffer(self) -> bytearray:
        return self._state.fast_buffer

    @property
    def parse_position(self) -> int:
        return self._state.parse_position

    @parse_position.setter
    def parse_position(self, value: int) -> None:
        self._state.parse_position = value

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data_gen incrementally using Ultra-JSON style optimization.

        Args:
            buffer: String chunk of JSON data_gen to process
        """
        if not buffer:
            return

        self.buffer += buffer
        buffer_bytes = self._convert_to_bytes(buffer)
        self.fast_buffer.extend(buffer_bytes)
        self._parse_ultra_fast()

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

    @staticmethod
    def _convert_to_bytes(buffer: str) -> bytearray:
        """Convert string buffer to bytes for faster processing."""
        return bytearray(buffer.encode('utf-8'))

    def _parse_ultra_fast(self) -> None:
        """Parse using Ultra-JSON inspired fast parsing techniques."""
        while self._has_more_data():
            obj_boundaries = self._find_next_object_boundaries()

            if not obj_boundaries:
                break

            obj_start, obj_end = obj_boundaries
            if self._is_complete_object(obj_start, obj_end):
                self._process_complete_object(obj_start, obj_end)
                self.parse_position = obj_end + 1
            else:
                break

    def _has_more_data(self) -> bool:
        """Check if there's more data_gen to parse."""
        return self.parse_position < len(self.fast_buffer)

    def _find_next_object_boundaries(self) -> Optional[Tuple[int, int]]:
        """Find the boundaries of the next JSON object."""
        obj_start = self._fast_find_object_start(self.parse_position)
        if obj_start < 0:
            return None

        obj_end = self._fast_find_object_end(obj_start)
        if obj_end <= obj_start:
            return None

        return obj_start, obj_end

    @staticmethod
    def _is_complete_object(obj_start: int, obj_end: int) -> bool:
        """Check if object boundaries represent a complete object."""
        return obj_end > obj_start

    def _process_complete_object(self, obj_start: int, obj_end: int) -> None:
        """Process a complete JSON object."""
        obj_bytes = self.fast_buffer[obj_start:obj_end + 1]
        self._parse_fast_object(obj_bytes)

    def _fast_find_object_start(self, start_pos: int) -> int:
        """Fast scan for object start using Ultra-JSON style byte scanning."""
        return self._find_byte_position(start_pos, ord('{'))

    def _find_byte_position(self, start_pos: int, target_byte: int) -> int:
        """Find position of target byte in buffer."""
        for i in range(start_pos, len(self.fast_buffer)):
            if self.fast_buffer[i] == target_byte:
                return i
        return -1

    def _fast_find_object_end(self, start_pos: int) -> int:
        """Fast scan for the object end with minimal overhead."""
        parser_state = ObjectEndParserState()

        for i in range(start_pos, len(self.fast_buffer)):
            byte_val = self.fast_buffer[i]

            if self._should_skip_byte(parser_state, byte_val):
                continue

            self._update_parser_state(parser_state, byte_val)

            if self._is_object_complete(parser_state):
                return i

        return -1

    @staticmethod
    def _should_skip_byte(state: 'ObjectEndParserState', byte_val: int) -> bool:
        """Check if the current byte should be skipped during parsing."""
        if state.escape_next:
            state.escape_next = False
            return True

        if byte_val == ord('\\'):
            state.escape_next = True
            return True

        return False

    @staticmethod
    def _update_parser_state(state: 'ObjectEndParserState', byte_val: int) -> None:
        """Update parser state based on current byte."""
        if byte_val == ord('"') and not state.escape_next:
            state.in_string = not state.in_string
            return

        if not state.in_string:
            if byte_val == ord('{'):
                state.brace_count += 1
            elif byte_val == ord('}'):
                state.brace_count -= 1

    @staticmethod
    def _is_object_complete(state: 'ObjectEndParserState') -> bool:
        """Check if object parsing is complete."""
        return not state.in_string and state.brace_count == 0

    def _parse_fast_object(self, obj_bytes: bytearray) -> None:
        """Parse object using Ultra-JSON style fast parsing."""
        try:
            parsed_obj = self._try_standard_json_parse(obj_bytes)
            if parsed_obj:
                self._update_parsed_data(parsed_obj)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._ultra_fast_partial_parse(obj_bytes)

    @staticmethod
    def _try_standard_json_parse(obj_bytes: bytearray) -> Optional[Dict[str, Any]]:
        """Attempt standard JSON parsing."""
        try:
            obj_str = obj_bytes.decode('utf-8')
            obj = json.loads(obj_str)
            return obj if isinstance(obj, dict) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _update_parsed_data(self, obj: Dict[str, Any]) -> None:
        """Update parsed data_gen with complete key-value pairs."""
        complete_pairs = self._fast_extract_complete_pairs(obj)
        self.parsed_data.update(complete_pairs)

    @staticmethod
    def _fast_extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Fast extraction of complete key-value pairs."""
        return {
            key: value
            for key, value in obj.items()
            if isinstance(key, str) and key
        }

    def _ultra_fast_partial_parse(self, obj_bytes: bytearray) -> None:
        """Ultra-fast partial parsing for incomplete objects."""
        try:
            obj_str = self._safe_decode_bytes(obj_bytes)
            balanced_obj = self._try_balance_and_parse(obj_str)

            if balanced_obj:
                self._update_parsed_data(balanced_obj)
            else:
                self._ultra_fast_field_extraction(obj_str)
        except ValueError:
            pass

    @staticmethod
    def _safe_decode_bytes(obj_bytes: bytearray) -> str:
        """Safely decode bytes to string with error handling."""
        return obj_bytes.decode('utf-8', errors='replace')

    def _try_balance_and_parse(self, obj_str: str) -> Optional[Dict[str, Any]]:
        """Try to balance braces and parse the object."""
        brace_balance = self._calculate_brace_balance(obj_str)

        if brace_balance <= 0:
            return None

        balanced_str = obj_str + '}' * brace_balance

        try:
            obj = json.loads(balanced_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _calculate_brace_balance(obj_str: str) -> int:
        """Calculate the balance of opening vs. closing braces."""
        open_braces = obj_str.count('{')
        close_braces = obj_str.count('}')
        return open_braces - close_braces

    def _ultra_fast_field_extraction(self, obj_str: str) -> None:
        """Ultra-fast field extraction using minimal parsing."""
        try:
            extracted_fields = self._extract_key_value_pairs(obj_str)
            if extracted_fields:
                self.parsed_data.update(extracted_fields)
        except ValueError:
            pass

    def _extract_key_value_pairs(self, obj_str: str) -> Dict[str, Any]:
        """Extract key-value pairs from string using fast parsing."""
        result = {}
        position = 0

        while position < len(obj_str):
            key_info = self._find_next_key(obj_str, position)
            if not key_info:
                break

            key, key_end_pos = key_info
            value_info = self._find_value_for_key(obj_str, key_end_pos)

            if value_info:
                value, next_position = value_info
                result[key] = value
                position = next_position
            else:
                position = key_end_pos + 1

        return result

    @staticmethod
    def _find_next_key(obj_str: str, start_pos: int) -> Optional[Tuple[str, int]]:
        """Find the next key in the JSON string."""
        quote_pos = obj_str.find('"', start_pos)
        if quote_pos == -1:
            return None

        key_start = quote_pos + 1
        key_end = obj_str.find('"', key_start)

        if key_end <= key_start:
            return None

        key = obj_str[key_start:key_end]
        return key, key_end

    @staticmethod
    def _find_value_for_key(obj_str: str, key_end_pos: int) -> Optional[Tuple[Any, int]]:
        """Find the value associated with a key."""
        colon_pos = obj_str.find(':', key_end_pos)
        if colon_pos == -1:
            return None

        value_start = StreamingJsonParser._skip_whitespace(obj_str, colon_pos + 1)
        if value_start >= len(obj_str):
            return None

        value = StreamingJsonParser._fast_extract_value(obj_str, value_start)
        if value is None:
            return None

        return value, value_start + 1

    @staticmethod
    def _skip_whitespace(obj_str: str, start_pos: int) -> int:
        """Skip whitespace characters starting from position."""
        while start_pos < len(obj_str) and obj_str[start_pos].isspace():
            start_pos += 1
        return start_pos

    @staticmethod
    def _fast_extract_value(obj_str: str, start_pos: int) -> Any:
        """Fast value extraction with minimal overhead."""
        if start_pos >= len(obj_str):
            return None

        char = obj_str[start_pos]

        if char == '"':
            return StreamingJsonParser._extract_string_value(obj_str, start_pos)
        elif char.isdigit() or char == '-':
            return StreamingJsonParser._extract_number_value(obj_str, start_pos)
        else:
            return StreamingJsonParser._extract_literal_value(obj_str, start_pos)

    @staticmethod
    def _extract_string_value(obj_str: str, start_pos: int) -> Optional[str]:
        """Extract string value from JSON."""
        end_pos = obj_str.find('"', start_pos + 1)
        return obj_str[start_pos + 1:end_pos] if end_pos > start_pos else None

    @staticmethod
    def _extract_number_value(obj_str: str, start_pos: int) -> Any:
        """Extract number value from JSON."""
        end_pos = start_pos + 1
        while (end_pos < len(obj_str) and
               (obj_str[end_pos].isdigit() or obj_str[end_pos] in '.-')):
            end_pos += 1

        num_str = obj_str[start_pos:end_pos]
        try:
            return int(num_str) if '.' not in num_str else float(num_str)
        except ValueError:
            return num_str

    @staticmethod
    def _extract_literal_value(obj_str: str, start_pos: int) -> Optional[Any]:
        """Extract literal values (true, false, null) from JSON."""
        remaining = obj_str[start_pos:].lower()

        if remaining.startswith('true'):
            return True
        elif remaining.startswith('false'):
            return False
        elif remaining.startswith('null'):
            return None

        return None


class ObjectEndParserState:
    """State tracker for object end parsing."""

    def __init__(self):
        self.brace_count = 0
        self.in_string = False
        self.escape_next = False
