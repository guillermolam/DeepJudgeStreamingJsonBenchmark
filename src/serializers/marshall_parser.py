
"""
Marshall serialization streaming parser implementation.
Note: Marshall is primarily for Python code objects, so this implements
a JSON-compatible streaming parser with marshall-like buffering strategy.
"""
import json
from typing import Any, Dict, List, Optional, Tuple


class StreamingJsonParser:
    """Streaming JSON parser with Marshall-inspired buffering strategy."""

    def __init__(self) -> None:
        """Initialize the streaming JSON parser with empty state."""
        self._buffer = ""
        self._parsed_data: Dict[str, Any] = {}

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally.

        Args:
            buffer: String chunk of JSON data to process
        """
        self._buffer += buffer
        self._process_buffer()

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.

        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self._parsed_data.copy()

    def _process_buffer(self) -> None:
        """Process the current buffer using Marshall-inspired strategy."""
        lines, remaining_buffer = self._split_buffer_into_lines()

        for line in lines:
            if self._is_valid_line(line):
                self._process_line(line)

        self._buffer = remaining_buffer

    def _split_buffer_into_lines(self) -> Tuple[List[str], str]:
        """
        Split buffer into processable lines and remaining buffer.

        Returns:
            Tuple of (complete_lines, remaining_incomplete_line)
        """
        lines = self._buffer.split('\\n')
        complete_lines = [line.strip() for line in lines[:-1]]
        remaining_buffer = lines[-1] if lines else ""

        return complete_lines, remaining_buffer

    @staticmethod
    def _is_valid_line(line: str) -> bool:
        """Check if line is worth processing (pure function)."""
        return bool(line.strip())

    def _process_line(self, line: str) -> None:
        """Process a single line, attempting complete then partial parsing."""
        complete_object = self._try_parse_complete_json(line)

        if complete_object is not None:
            self._merge_complete_pairs(complete_object)
        else:
            self._try_parse_partial_json(line)

    @staticmethod
    def _try_parse_complete_json(line: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse line as complete JSON (pure function).

        Returns:
            Parsed dictionary if successful, None otherwise
        """
        try:
            parsed = json.loads(line)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _merge_complete_pairs(self, obj: Dict[str, Any]) -> None:
        """Merge complete key-value pairs into parsed data."""
        complete_pairs = self._extract_valid_pairs(obj)
        self._parsed_data.update(complete_pairs)

    @staticmethod
    def _extract_valid_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract valid key-value pairs from an object (pure function).

        Args:
            obj: Dictionary to extract pairs from

        Returns:
            Dictionary with valid key-value pairs
        """
        return {
            key: value
            for key, value in obj.items()
            if isinstance(key, str) and key
        }

    def _try_parse_partial_json(self, line: str) -> None:
        """Attempt to parse partial JSON using progressive completion."""
        if not self._contains_json_structure(line):
            return

        partial_object = self._find_longest_valid_json_prefix(line)
        if partial_object is not None:
            self._merge_complete_pairs(partial_object)

    @staticmethod
    def _contains_json_structure(line: str) -> bool:
        """Check if line contains JSON structure markers (pure function)."""
        return '{' in line

    @staticmethod
    def _find_longest_valid_json_prefix(line: str) -> Optional[Dict[str, Any]]:
        """
        Find the longest valid JSON prefix in the line (pure function).

        Args:
            line: Line to analyze

        Returns:
            Parsed dictionary if valid prefix found, None otherwise
        """
        for end_pos in range(len(line), 0, -1):
            candidate = StreamingJsonParser._create_json_candidate(line, end_pos)

            if candidate is None:
                continue

            parsed = StreamingJsonParser._try_parse_complete_json(candidate)
            if parsed is not None:
                return parsed

        return None

    @staticmethod
    def _create_json_candidate(line: str, end_pos: int) -> Optional[str]:
        """
        Create a JSON candidate by balancing braces (pure function).

        Args:
            line: Original line
            end_pos: Position to cut the line

        Returns:
            Balanced JSON string or None if not viable
        """
        prefix = line[:end_pos]
        open_braces = prefix.count('{')
        close_braces = prefix.count('}')

        if open_braces <= close_braces:
            return None

        brace_diff = open_braces - close_braces
        return prefix + '}' * brace_diff
