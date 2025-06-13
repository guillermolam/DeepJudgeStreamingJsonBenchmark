"""
Single-threaded Pickle Binary streaming parser implementation.
Note: Pickle is for Python objects, so this implements JSON parsing
with Pickle-inspired single-threaded buffering and object reconstruction.
"""
import json
import pickle
import io
from typing import Any, Dict, Optional


class StreamingJsonParser:
    """Single-threaded streaming JSON parser with Pickle-inspired object handling."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.object_stack = []
        self.current_depth = 0

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer
        self._parse_single_threaded()

    def _parse_single_threaded(self) -> None:
        """Parse using single-threaded Pickle-inspired strategy."""
        # Process character by character like Pickle's single-threaded approach
        i = 0
        while i < len(self.buffer):
            char = self.buffer[i]

            if char == '{':
                self._handle_object_start(i)
            elif char == '}':
                self._handle_object_end(i)
            elif char == '"':
                self._handle_string_start(i)

            i += 1

    def _handle_object_start(self, position: int) -> None:
        """Handle start of JSON object."""
        self.current_depth += 1

        # Try to extract complete object from this position
        try:
            remaining = self.buffer[position:]
            obj_end = self._find_object_end(remaining)

            if obj_end > 0:
                json_str = remaining[:obj_end + 1]
                obj = json.loads(json_str)

                if isinstance(obj, dict):
                    complete_pairs = self._extract_complete_pairs(obj)
                    self.parsed_data.update(complete_pairs)

        except (json.JSONDecodeError, ValueError):
            # Try partial parsing
            self._try_partial_parse(position)

    def _handle_object_end(self, position: int) -> None:
        """Handle end of JSON object."""
        if self.current_depth > 0:
            self.current_depth -= 1

    def _handle_string_start(self, position: int) -> None:
        """Handle start of string value."""
        # Look for complete string values
        try:
            remaining = self.buffer[position:]
            string_end = self._find_string_end(remaining)

            if string_end > 0:
                # Found complete string, continue processing
                pass

        except Exception:
            pass

    def _find_object_end(self, json_str: str) -> int:
        """Find the end position of a complete JSON object."""
        brace_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(json_str):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i

        return -1

    def _find_string_end(self, json_str: str) -> int:
        """Find the end position of a string."""
        if not json_str.startswith('"'):
            return -1

        escape_next = False
        for i in range(1, len(json_str)):
            char = json_str[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"':
                return i

        return -1

    def _try_partial_parse(self, position: int) -> None:
        """Try to parse partial JSON objects."""
        remaining = self.buffer[position:]

        # Look for complete key-value pairs
        try:
            # Find potential end positions
            for end_pos in range(len(remaining), 0, -1):
                test_str = remaining[:end_pos]

                # Balance braces
                open_braces = test_str.count('{')
                close_braces = test_str.count('}')

                if open_braces > close_braces:
                    # Add missing closing braces
                    balanced_str = test_str + '}' * (open_braces - close_braces)

                    try:
                        obj = json.loads(balanced_str)
                        if isinstance(obj, dict):
                            complete_pairs = self._extract_complete_pairs(obj)
                            self.parsed_data.update(complete_pairs)
                            break
                    except json.JSONDecodeError:
                        continue

        except Exception:
            pass

    def _extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs, allowing partial string values."""
        complete_pairs = {}

        for key, value in obj.items():
            # Only include pairs with complete keys
            if isinstance(key, str) and len(key) > 0:
                # Partial string values are allowed
                complete_pairs[key] = value

        return complete_pairs

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()
