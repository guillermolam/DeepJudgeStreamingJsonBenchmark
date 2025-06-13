"""
BSON (Binary JSON) streaming parser implementation.
Note: BSON is binary format, so this implements JSON parsing
with BSON-inspired binary-like chunking and type handling.
"""
import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ParserState:
    """Internal mutable parser state."""

    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    binary_buffer: bytearray = field(default_factory=bytearray)
    document_length: Optional[int] = None
    current_position: int = 0


class StreamingJsonParser:
    """Streaming JSON parser with BSON-inspired binary chunking and type handling."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._state = ParserState()

    # Properties to expose internal state
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
    def binary_buffer(self) -> bytearray:
        return self._state.binary_buffer

    @property
    def document_length(self) -> Optional[int]:
        return self._state.document_length

    @document_length.setter
    def document_length(self, value: Optional[int]) -> None:
        self._state.document_length = value

    @property
    def current_position(self) -> int:
        return self._state.current_position

    @current_position.setter
    def current_position(self, value: int) -> None:
        self._state.current_position = value

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data_gen incrementally using BSON-style processing.

        Args:
            buffer: String chunk of JSON data_gen to process
        """
        self.buffer += buffer
        self._add_to_binary_buffer(buffer)
        self._parse_bson_style()

    def _add_to_binary_buffer(self, buffer: str) -> None:
        """Add buffer to binary buffer for BSON-style processing."""
        buffer_bytes = buffer.encode('utf-8')
        self.binary_buffer.extend(buffer_bytes)

    def _parse_bson_style(self) -> None:
        """Parse using BSON-inspired document structure."""
        while self._has_remaining_data():
            if not self._try_read_document_length():
                break

            if not self._try_process_document():
                break

    def _has_remaining_data(self) -> bool:
        """Check if there's remaining data_gen to process."""
        return self.current_position < len(self.binary_buffer)

    def _try_read_document_length(self) -> bool:
        """Try to read document length in BSON style."""
        if self.document_length is not None:
            return True

        if not self._has_enough_bytes_for_length():
            return False

        return self._read_length_or_fallback()

    def _has_enough_bytes_for_length(self) -> bool:
        """Check if we have enough bytes to read the length field."""
        return len(self.binary_buffer) - self.current_position >= 4

    def _read_length_or_fallback(self) -> bool:
        """Read length as BSON format or fallback to JSON parsing."""
        try:
            self._read_bson_length()
            return True
        except struct.error:
            self._parse_json_documents()
            return False

    def _read_bson_length(self) -> None:
        """Read BSON document length from buffer."""
        length_bytes = self.binary_buffer[self.current_position:self.current_position + 4]
        self.document_length = struct.unpack('<I', length_bytes)[0]
        self.current_position += 4

    def _try_process_document(self) -> bool:
        """Try to process a complete document."""
        if self.document_length is None:
            return True

        remaining_bytes = len(self.binary_buffer) - self.current_position
        required_bytes = self.document_length - 4  # -4 for length field

        if remaining_bytes < required_bytes:
            return False

        self._process_complete_document(required_bytes)
        return True

    def _process_complete_document(self, doc_size: int) -> None:
        """Process a complete BSON document."""
        doc_bytes = self.binary_buffer[self.current_position:self.current_position + doc_size]
        self.current_position += doc_size
        self._process_bson_document(doc_bytes)
        self.document_length = None

    def _parse_json_documents(self) -> None:
        """Fallback to JSON document parsing."""
        try:
            remaining_str = self._get_remaining_string()
            self._extract_json_documents(remaining_str)
            self._clear_processed_data()
        except ValueError:
            pass

    def _get_remaining_string(self) -> str:
        """Get the remaining buffer as string."""
        return self.binary_buffer[self.current_position:].decode('utf-8', errors='ignore')

    def _clear_processed_data(self) -> None:
        """Clear processed binary data_gen."""
        self.binary_buffer.clear()
        self.current_position = 0

    def _process_bson_document(self, doc_bytes: bytearray) -> None:
        """Process a BSON-style document."""
        try:
            doc_str = doc_bytes.decode('utf-8', errors='replace')
            self._try_parse_as_json(doc_str)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._parse_bson_fields(doc_bytes)

    def _try_parse_as_json(self, doc_str: str) -> None:
        """Try to parse document string as JSON."""
        obj = json.loads(doc_str)
        if isinstance(obj, dict):
            complete_pairs = self._extract_complete_pairs_bson(obj)
            self.parsed_data.update(complete_pairs)

    def _parse_bson_fields(self, doc_bytes: bytearray) -> None:
        """Parse BSON-style fields from document bytes."""
        try:
            doc_str = doc_bytes.decode('utf-8', errors='replace')
            if '{' in doc_str:
                self._extract_json_documents(doc_str)
        except ValueError:
            pass

    def _extract_json_documents(self, text: str) -> None:
        """Extract JSON documents using BSON-inspired parsing."""
        parser_state = self._create_parser_state()

        for char in text:
            self._process_character(char, parser_state)

        self._handle_remaining_document(parser_state)

    @staticmethod
    def _create_parser_state() -> Dict[str, Any]:
        """Create initial parser state."""
        return {
            'current_doc': "",
            'brace_count': 0,
            'in_string': False,
            'escape_next': False
        }

    def _process_character(self, char: str, state: Dict[str, Any]) -> None:
        """Process a single character in the parsing state."""
        state['current_doc'] += char

        if state['escape_next']:
            state['escape_next'] = False
            return

        if char == '\\':
            state['escape_next'] = True
            return

        if self._is_string_delimiter(char, state):
            return

        self._handle_brace_character(char, state)

    @staticmethod
    def _is_string_delimiter(char: str, state: Dict[str, Any]) -> bool:
        """Handle string delimiter character."""
        if char == '"' and not state['escape_next']:
            state['in_string'] = not state['in_string']
            return True
        return False

    def _handle_brace_character(self, char: str, state: Dict[str, Any]) -> None:
        """Handle brace characters for document parsing."""
        if state['in_string']:
            return

        if char == '{':
            state['brace_count'] += 1
        elif char == '}':
            state['brace_count'] -= 1
            if state['brace_count'] == 0 and state['current_doc'].strip():
                self._process_complete_json_document(state['current_doc'].strip())
                state['current_doc'] = ""

    def _process_complete_json_document(self, doc_str: str) -> None:
        """Process a complete JSON document."""
        try:
            obj = json.loads(doc_str)
            if isinstance(obj, dict):
                complete_pairs = self._extract_complete_pairs_bson(obj)
                self.parsed_data.update(complete_pairs)
        except json.JSONDecodeError:
            self._try_partial_bson_parse(doc_str)

    def _handle_remaining_document(self, state: Dict[str, Any]) -> None:
        """Handle any remaining incomplete document."""
        if state['current_doc'].strip() and state['brace_count'] > 0:
            self._try_partial_bson_parse(state['current_doc'].strip())

    def _try_partial_bson_parse(self, doc_str: str) -> None:
        """Try to parse partial BSON document."""
        if not self._contains_json_structure(doc_str):
            return

        balanced_doc = self._balance_json_braces(doc_str)
        if balanced_doc:
            self._try_parse_balanced_document(balanced_doc)

    @staticmethod
    def _contains_json_structure(doc_str: str) -> bool:
        """Check if document contains JSON structure."""
        return '{' in doc_str

    @staticmethod
    def _balance_json_braces(doc_str: str) -> str:
        """Balance JSON braces in document."""
        open_braces = doc_str.count('{')
        close_braces = doc_str.count('}')

        if open_braces > close_braces:
            return doc_str + '}' * (open_braces - close_braces)
        return ""

    def _try_parse_balanced_document(self, balanced_doc: str) -> None:
        """Try to parse a balanced JSON document."""
        try:
            obj = json.loads(balanced_doc)
            if isinstance(obj, dict):
                complete_pairs = self._extract_complete_pairs_bson(obj)
                self.parsed_data.update(complete_pairs)
        except json.JSONDecodeError:
            pass

    def _extract_complete_pairs_bson(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with BSON-style type validation."""
        complete_pairs = {}

        for key, value in obj.items():
            if self._is_valid_bson_key(key) and self._is_valid_bson_value(value):
                complete_pairs[key] = value

        return complete_pairs

    @staticmethod
    def _is_valid_bson_key(key: Any) -> bool:
        """Check if the key is valid for BSON."""
        return isinstance(key, str) and len(key) > 0

    def _is_valid_bson_value(self, value: Any) -> bool:
        """Check if the value is valid for BSON-style storage."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return True

        if isinstance(value, list):
            return self._is_valid_bson_array(value)

        if isinstance(value, dict):
            return self._is_valid_bson_object(value)

        return False

    def _is_valid_bson_array(self, array: list) -> bool:
        """Check an if an array is valid for BSON."""
        return all(self._is_valid_bson_value(item) for item in array)

    def _is_valid_bson_object(self, obj: dict) -> bool:
        """Check if an object is valid for BSON."""
        return all(isinstance(k, str) and self._is_valid_bson_value(v)
                   for k, v in obj.items())

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
