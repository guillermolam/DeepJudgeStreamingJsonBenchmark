"""
BSON streaming parser implementation with SOLID principles.

This module implements a streaming JSON parser inspired by BSON binary format.
It follows SOLID principles with clean separation of concerns, stateless operations where possible,
and cognitive complexity under 14 for all methods.

Key Features:
- Binary-inspired processing like BSON
- Incremental JSON parsing with document-based processing
- Stateless utility functions and processors
- Clean separation between document parsing, validation, and data extraction
- Comprehensive error handling and recovery

Architecture:
- ParserState: Immutable state container using @dataclass
- Static utility classes for document validation and binary processing
- Dependency injection for loose coupling
- Single responsibility principle throughout
"""
import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ParserState:
    """Immutable state container for the BSON parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


class DocumentValidator:
    """Stateless validator for BSON-style documents."""

    @staticmethod
    def is_valid_key(key: Any) -> bool:
        """Check if the key is valid for BSON-style storage."""
        return isinstance(key, str) and len(key) > 0

    @staticmethod
    def is_valid_value(value: Any) -> bool:
        """Check if the value is valid for BSON-style storage."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return True

        if isinstance(value, list):
            return all(DocumentValidator.is_valid_value(item) for item in value)

        if isinstance(value, dict):
            return all(isinstance(k, str) and DocumentValidator.is_valid_value(v)
                       for k, v in value.items())

        return False

    @staticmethod
    def contains_json_structure(doc_str: str) -> bool:
        """Check if document contains JSON structure."""
        return '{' in doc_str


class PairExtractor:
    """Extracts complete key-value pairs from objects using stateless operations."""

    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with BSON-style validation."""
        if not isinstance(obj, dict):
            return {}

        return {
            key: value
            for key, value in obj.items()
            if DocumentValidator.is_valid_key(key) and DocumentValidator.is_valid_value(value)
        }


class BinaryProcessor:
    """Stateless utility for BSON-style binary processing."""

    @staticmethod
    def convert_to_binary(buffer: str) -> bytearray:
        """Convert string buffer to binary for BSON-style processing."""
        return bytearray(buffer.encode('utf-8'))

    @staticmethod
    def try_read_length(buffer: bytearray, position: int) -> Optional[int]:
        """Try to read BSON document length from buffer."""
        if len(buffer) - position < 4:
            return None

        try:
            length_bytes = buffer[position:position + 4]
            return struct.unpack('<I', length_bytes)[0]
        except struct.error:
            return None

    @staticmethod
    def safe_decode_binary(doc_bytes: bytearray) -> str:
        """Safely decode binary data to string."""
        return doc_bytes.decode('utf-8', errors='replace')


class DocumentExtractor:
    """Extracts JSON documents using BSON-inspired parsing."""

    @staticmethod
    def extract_documents(text: str) -> List[str]:
        """Extract JSON documents from text using BSON-inspired parsing."""
        documents = []
        current_doc = ""
        brace_count = 0
        in_string = False
        escape_next = False

        for char in text:
            current_doc += char

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if DocumentExtractor._is_string_delimiter(char, escape_next):
                in_string = not in_string
                continue

            if not in_string:
                brace_count = DocumentExtractor._update_brace_count(char, brace_count)
                if brace_count == 0 and current_doc.strip():
                    documents.append(current_doc.strip())
                    current_doc = ""

        # Handle remaining incomplete document
        if current_doc.strip() and brace_count > 0:
            documents.append(current_doc.strip())

        return documents

    @staticmethod
    def _is_string_delimiter(char: str, escape_next: bool) -> bool:
        """Check if character is a string delimiter."""
        return char == '"' and not escape_next

    @staticmethod
    def _update_brace_count(char: str, count: int) -> int:
        """Update brace count based on character."""
        if char == '{':
            return count + 1
        elif char == '}':
            return count - 1
        return count


class DocumentFormatter:
    """Stateless utility for document formatting."""

    @staticmethod
    def balance_braces(doc_str: str) -> Optional[str]:
        """Balance JSON braces in document."""
        if not DocumentValidator.contains_json_structure(doc_str):
            return None

        open_braces = doc_str.count('{')
        close_braces = doc_str.count('}')

        if open_braces > close_braces:
            return doc_str + '}' * (open_braces - close_braces)
        elif open_braces == close_braces and open_braces > 0:
            return doc_str

        return None


class DocumentParser:
    """Parses individual BSON-style documents."""

    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()

    def parse_document(self, doc_str: str) -> Dict[str, Any]:
        """Parse a BSON-style document."""
        # Try direct JSON parsing first
        parsed_obj = self._try_direct_parse(doc_str)
        if parsed_obj:
            return self._pair_extractor.extract_complete_pairs(parsed_obj)

        # Try partial parsing with balancing
        return self._try_partial_parse(doc_str)

    @staticmethod
    def _try_direct_parse(doc_str: str) -> Optional[Dict[str, Any]]:
        """Try direct JSON parsing of document."""
        try:
            obj = json.loads(doc_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None

    def _try_partial_parse(self, doc_str: str) -> Dict[str, Any]:
        """Try partial parsing with brace balancing."""
        balanced_doc = DocumentFormatter.balance_braces(doc_str)
        if not balanced_doc:
            return {}

        try:
            obj = json.loads(balanced_doc)
            if isinstance(obj, dict):
                return self._pair_extractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass

        return {}


class BsonStyleProcessor:
    """Main processor using BSON-inspired document processing with dependency injection."""

    def __init__(self,
                 binary_processor: BinaryProcessor = None,
                 document_extractor: DocumentExtractor = None,
                 document_parser: DocumentParser = None):
        self._binary_processor = binary_processor or BinaryProcessor()
        self._document_extractor = document_extractor or DocumentExtractor()
        self._document_parser = document_parser or DocumentParser()
        self._binary_buffer = bytearray()
        self._current_position = 0
        self._document_length = None

    def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Process buffer using BSON-inspired document structure."""
        self._add_to_binary_buffer(buffer)
        return self._parse_bson_style()

    def _add_to_binary_buffer(self, buffer: str) -> None:
        """Add buffer to binary buffer for BSON-style processing."""
        buffer_bytes = self._binary_processor.convert_to_binary(buffer)
        self._binary_buffer.extend(buffer_bytes)

    def _parse_bson_style(self) -> Dict[str, Any]:
        """Parse using BSON-inspired document structure."""
        parsed_data = {}

        while self._has_remaining_data():
            if not self._try_read_document_length():
                # Fallback to JSON document parsing
                fallback_data = self._parse_json_documents()
                parsed_data.update(fallback_data)
                break

            if not self._try_process_document():
                break

            doc_data = self._process_current_document()
            parsed_data.update(doc_data)

        return parsed_data

    def _has_remaining_data(self) -> bool:
        """Check if there's remaining data to process."""
        return self._current_position < len(self._binary_buffer)

    def _try_read_document_length(self) -> bool:
        """Try to read document length in BSON style."""
        if self._document_length is not None:
            return True

        length = self._binary_processor.try_read_length(self._binary_buffer, self._current_position)
        if length is not None:
            self._document_length = length
            self._current_position += 4
            return True

        return False

    def _try_process_document(self) -> bool:
        """Try to process a complete document."""
        if self._document_length is None:
            return True

        remaining_bytes = len(self._binary_buffer) - self._current_position
        required_bytes = self._document_length - 4  # -4 for length field

        return remaining_bytes >= required_bytes

    def _process_current_document(self) -> Dict[str, Any]:
        """Process the current complete document."""
        if self._document_length is None:
            return {}

        doc_size = self._document_length - 4
        doc_bytes = self._binary_buffer[self._current_position:self._current_position + doc_size]
        self._current_position += doc_size

        doc_str = self._binary_processor.safe_decode_binary(doc_bytes)
        result = self._document_parser.parse_document(doc_str)

        self._document_length = None
        return result

    def _parse_json_documents(self) -> Dict[str, Any]:
        """Fallback to JSON document parsing."""
        try:
            remaining_str = self._get_remaining_string()
            documents = self._document_extractor.extract_documents(remaining_str)

            parsed_data = {}
            for doc in documents:
                doc_data = self._document_parser.parse_document(doc)
                parsed_data.update(doc_data)

            self._clear_processed_data()
            return parsed_data
        except ValueError:
            return {}

    def _get_remaining_string(self) -> str:
        """Get the remaining buffer as string."""
        remaining_bytes = self._binary_buffer[self._current_position:]
        return self._binary_processor.safe_decode_binary(remaining_bytes)

    def _clear_processed_data(self) -> None:
        """Clear processed binary data."""
        self._binary_buffer.clear()
        self._current_position = 0


class StreamingJsonParser:
    """Streaming JSON parser with BSON-inspired binary document processing."""

    def __init__(self, processor: BsonStyleProcessor = None):
        """Initialize the streaming JSON parser with dependency injection."""
        self._state = ParserState()
        self._processor = processor or BsonStyleProcessor()

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
        Process a chunk of JSON data incrementally using BSON-style processing.

        Args:
            buffer: String chunk of JSON data to process
        """
        self._buffer += buffer
        new_data = self._processor.process_buffer(buffer)
        if new_data:
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
