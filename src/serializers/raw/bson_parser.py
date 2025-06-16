"""
BSON (Binary JSON) streaming parser implementation.
Note: BSON is binary format, so this implements JSON parsing
with BSON-inspired binary-like chunking and type handling.
"""
import json as JsonParser
from typing import Any, Dict
import struct


class StreamingJsonParser:
    """Streaming JSON parser with BSON-inspired binary chunking and type handling."""

    def __init__(self):
        """Initialize the streaming JSON parser."""
        self.buffer = ""
        self.parsed_data = {}
        self.binary_buffer = bytearray()
        self.document_length = None
        self.current_position = 0

    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using BSON-style processing.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self.buffer += buffer

        # Convert to binary representation for BSON-style processing
        buffer_bytes = buffer.encode('utf-8')
        self.binary_buffer.extend(buffer_bytes)

        self._parse_bson_style()

    def _parse_bson_style(self) -> None:
        """Parse using BSON-inspired document structure."""
        # BSON documents start with a 4-byte length field
        # Here we simulate this by looking for complete JSON documents

        while self.current_position < len(self.binary_buffer):
            # Try to read document length (BSON-style)
            if self.document_length is None:
                if len(self.binary_buffer) - self.current_position >= 4:
                    try:
                        # Try to read length as little-endian 32-bit int (BSON format)
                        length_bytes = self.binary_buffer[self.current_position:self.current_position + 4]
                        self.document_length = struct.unpack('<I', length_bytes)[0]
                        self.current_position += 4
                    except struct.error:
                        # Fallback to JSON-based parsing
                        self._parse_json_documents()
                        break
                else:
                    break

            # Read document of specified length
            if self.document_length is not None:
                remaining_bytes = len(self.binary_buffer) - self.current_position
                if remaining_bytes >= self.document_length - 4:  # -4 for length field
                    doc_bytes = self.binary_buffer[
                                self.current_position:self.current_position + self.document_length - 4]
                    self.current_position += self.document_length - 4

                    # Process BSON-style document
                    self._process_bson_document(doc_bytes)
                    self.document_length = None
                else:
                    break

    def _parse_json_documents(self) -> None:
        """Fallback to JSON document parsing."""
        try:
            # Convert remaining buffer to string
            remaining_str = self.binary_buffer[self.current_position:].decode('utf-8', errors='ignore')

            # Look for complete JSON documents
            self._extract_json_documents(remaining_str)

            # Clear processed data
            self.binary_buffer.clear()
            self.current_position = 0

        except Exception:
            pass

    def _process_bson_document(self, doc_bytes: bytearray) -> None:
        """Process a BSON-style document."""
        try:
            # Convert bytes back to string for JSON parsing
            doc_str = doc_bytes.decode('utf-8', errors='replace')

            # Parse as JSON
            obj = JsonParser.loads(doc_str)
            if isinstance(obj, dict):
                complete_pairs = self._extract_complete_pairs_bson(obj)
                self.parsed_data.update(complete_pairs)

        except (UnicodeDecodeError, json.JSONDecodeError):
            # Try BSON-style field parsing
            self._parse_bson_fields(doc_bytes)

    def _parse_bson_fields(self, doc_bytes: bytearray) -> None:
        """Parse BSON-style fields from document bytes."""
        try:
            # Convert to string and look for JSON patterns
            doc_str = doc_bytes.decode('utf-8', errors='replace')

            if '{' in doc_str:
                self._extract_json_documents(doc_str)

        except Exception:
            pass

    def _extract_json_documents(self, text: str) -> None:
        """Extract JSON documents using BSON-inspired parsing."""
        # BSON documents are self-contained, so look for complete JSON objects
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

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

                    if brace_count == 0 and current_doc.strip():
                        # Found complete document
                        try:
                            obj = json.loads(current_doc.strip())
                            if isinstance(obj, dict):
                                complete_pairs = self._extract_complete_pairs_bson(obj)
                                self.parsed_data.update(complete_pairs)
                        except json.JSONDecodeError:
                            # Try partial parsing
                            self._try_partial_bson_parse(current_doc.strip())

                        current_doc = ""

        # Handle remaining incomplete document
        if current_doc.strip() and brace_count > 0:
            self._try_partial_bson_parse(current_doc.strip())

    def _try_partial_bson_parse(self, doc_str: str) -> None:
        """Try to parse partial BSON document."""
        try:
            # BSON-style partial parsing: balance the document
            if '{' in doc_str:
                open_braces = doc_str.count('{')
                close_braces = doc_str.count('}')

                if open_braces > close_braces:
                    # Add missing closing braces
                    balanced_doc = doc_str + '}' * (open_braces - close_braces)

                    try:
                        obj = json.loads(balanced_doc)
                        if isinstance(obj, dict):
                            complete_pairs = self._extract_complete_pairs_bson(obj)
                            self.parsed_data.update(complete_pairs)
                    except json.JSONDecodeError:
                        pass

        except Exception:
            pass

    def _extract_complete_pairs_bson(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with BSON-style type validation."""
        complete_pairs = {}

        for key, value in obj.items():
            # BSON has specific type requirements
            if isinstance(key, str) and len(key) > 0:
                # BSON supports various types - validate value types
                if self._is_valid_bson_value(value):
                    complete_pairs[key] = value

        return complete_pairs

    def _is_valid_bson_value(self, value: Any) -> bool:
        """Check if value is valid for BSON-style storage."""
        # BSON supports: string, int32, int64, double, boolean, null, array, document
        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(self._is_valid_bson_value(item) for item in value)
        if isinstance(value, dict):
            return all(isinstance(k, str) and self._is_valid_bson_value(v)
                       for k, v in value.items())

        return False

    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self.parsed_data.copy()
