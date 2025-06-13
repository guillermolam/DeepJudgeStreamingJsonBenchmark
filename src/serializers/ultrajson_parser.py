"""
Ultra-JSON (ujson) streaming parser implementation.
Uses ujson-inspired high-performance parsing techniques for streaming JSON.
"""
import sys
import json
from typing import Any, Dict
from pathlib import Path

# Add src/ to sys.path so Python can find your packages
sys.path.insert(0, str(Path(__file__).parent / "src"))

def _fast_extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Fast extraction of complete key-value pairs."""
    # Ultra-JSON style: minimal validation for speed
    complete_pairs = {}

    for key, value in obj.items():
        # Fast validation: check key is non-empty string
        if isinstance(key, str) and key:
            # Partial string values allowed per requirements
            complete_pairs[key] = value

    return complete_pairs


def _fast_extract_value(obj_str: str, start_pos: int) -> Any:
    """Fast value extraction with minimal overhead."""
    try:
        if start_pos >= len(obj_str):
            return None

        char = obj_str[start_pos]

        if char == '"':
            # String value
            end_pos = obj_str.find('"', start_pos + 1)
            if end_pos > start_pos:
                return obj_str[start_pos + 1:end_pos]
        elif char.isdigit() or char == '-':
            # Number value
            end_pos = start_pos + 1
            while end_pos < len(obj_str) and (obj_str[end_pos].isdigit() or obj_str[end_pos] in '.-'):
                end_pos += 1

            num_str = obj_str[start_pos:end_pos]
            try:
                return int(num_str) if '.' not in num_str else float(num_str)
            except ValueError:
                return num_str
        elif obj_str[start_pos:start_pos + 4].lower() == 'true':
            return True
        elif obj_str[start_pos:start_pos + 5].lower() == 'false':
            return False
        elif obj_str[start_pos:start_pos + 4].lower() == 'null':
            return None

        return None

    except Exception:
        return None


class StreamingJsonParser:
    """Streaming JSON parser with Ultra-JSON inspired high-performance techniques."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.fast_buffer = bytearray()
        self.parse_position = 0

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using Ultra-JSON style optimization.

        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer

        # Convert to bytes for faster processing (ujson-style)
        buffer_bytes = buffer.encode('utf-8')
        self.fast_buffer.extend(buffer_bytes)

        self._parse_ultra_fast()

    def _parse_ultra_fast(self) -> None:
        """Parse using Ultra-JSON inspired fast parsing techniques."""
        # Ultra-JSON optimizations: minimal allocations, fast character scanning

        while self.parse_position < len(self.fast_buffer):
            # Fast scan for JSON object boundaries
            obj_start = self._fast_find_object_start(self.parse_position)

            if obj_start >= 0:
                obj_end = self._fast_find_object_end(obj_start)

                if obj_end > obj_start:
                    # Extract and parse an object
                    obj_bytes = self.fast_buffer[obj_start:obj_end + 1]
                    self._parse_fast_object(obj_bytes)
                    self.parse_position = obj_end + 1
                else:
                    # Incomplete object, wait for more data
                    break
            else:
                # No more objects found
                break

    def _fast_find_object_start(self, start_pos: int) -> int:
        """Fast scan for object start using Ultra-JSON style byte scanning."""
        # Scan bytes directly for performance
        for i in range(start_pos, len(self.fast_buffer)):
            if self.fast_buffer[i] == ord('{'):
                return i
        return -1

    def _fast_find_object_end(self, start_pos: int) -> int:
        """Fast scan for the object end with minimal overhead."""
        brace_count = 0
        in_string = False
        escape_next = False

        for i in range(start_pos, len(self.fast_buffer)):
            byte_val = self.fast_buffer[i]

            if escape_next:
                escape_next = False
                continue

            if byte_val == ord('\\'):
                escape_next = True
                continue

            if byte_val == ord('"') and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if byte_val == ord('{'):
                    brace_count += 1
                elif byte_val == ord('}'):
                    brace_count -= 1
                    if brace_count == 0:
                        return i

        return -1

    def _parse_fast_object(self, obj_bytes: bytearray) -> None:
        """Parse object using Ultra-JSON style fast parsing."""
        try:
            # Convert bytes to string with minimal overhead
            obj_str = obj_bytes.decode('utf-8')

            # Use standard JSON parser (ujson would be faster but not available)
            obj = json.loads(obj_str)

            if isinstance(obj, dict):
                # Fast extraction of complete pairs
                complete_pairs = _fast_extract_complete_pairs(obj)
                self.parsed_data.update(complete_pairs)

        except (UnicodeDecodeError, json.JSONDecodeError):
            # Try ultra-fast partial parsing
            self._ultra_fast_partial_parse(obj_bytes)

    def _ultra_fast_partial_parse(self, obj_bytes: bytearray) -> None:
        """Ultra-fast partial parsing for incomplete objects."""
        try:
            # Fast string conversion with error handling
            obj_str = obj_bytes.decode('utf-8', errors='replace')

            # Quick balance check
            open_braces = obj_str.count('{')
            close_braces = obj_str.count('}')

            if open_braces > close_braces:
                # Fast balance correction
                balanced_str = obj_str + '}' * (open_braces - close_braces)

                try:
                    obj = json.loads(balanced_str)
                    if isinstance(obj, dict):
                        complete_pairs = _fast_extract_complete_pairs(obj)
                        self.parsed_data.update(complete_pairs)
                except json.JSONDecodeError:
                    # Try ultra-fast field extraction
                    self._ultra_fast_field_extraction(obj_str)

        except Exception:
            pass

    def _ultra_fast_field_extraction(self, obj_str: str) -> None:
        """Ultra-fast field extraction using minimal parsing."""
        try:
            # Fast regex-free field extraction
            result = {}

            # Find key-value patterns quickly
            i = 0
            while i < len(obj_str):
                # Look for quoted strings (keys)
                if obj_str[i] == '"':
                    key_start = i + 1
                    key_end = obj_str.find('"', key_start)

                    if key_end > key_start:
                        key = obj_str[key_start:key_end]

                        # Look for colon
                        colon_pos = obj_str.find(':', key_end)
                        if colon_pos > key_end:
                            # Look for value
                            value_start = colon_pos + 1
                            while value_start < len(obj_str) and obj_str[value_start].isspace():
                                value_start += 1

                            if value_start < len(obj_str):
                                value = _fast_extract_value(obj_str, value_start)
                                if value is not None:
                                    result[key] = value

                        i = key_end + 1
                    else:
                        i += 1
                else:
                    i += 1

            if result:
                self.parsed_data.update(result)

        except Exception:
            pass

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()
