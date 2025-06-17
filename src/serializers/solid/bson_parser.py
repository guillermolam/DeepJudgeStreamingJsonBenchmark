"""
BSON streaming parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by BSON binary format.
The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original BSON-inspired helper classes remain but are no longer used by StreamingJsonParser.
"""

import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# --- Start of Refactored StreamingJsonParser and its dependencies ---
# (Identical to the implementation in raw/ultrajson_parser.py for consistency and compliance)

# State constants for the parser
_ST_EXPECT_OBJ_START = 0
_ST_EXPECT_KEY_START = 1  # After '{' or ','
_ST_IN_KEY = 2
_ST_IN_KEY_ESCAPE = 3
_ST_EXPECT_COLON = 4
_ST_EXPECT_VALUE_START = 5
_ST_IN_STRING_VALUE = 6
_ST_IN_STRING_VALUE_ESCAPE = 7
_ST_IN_NUMBER = 8
_ST_IN_TRUE = 9
_ST_IN_FALSE = 10
_ST_IN_NULL = 11
_ST_EXPECT_COMMA_OR_OBJ_END = 12
_ST_OBJ_END = 13
_ST_ERROR = 99

_WHITESPACE = b" \t\n\r"
_DIGITS = b"0123456789"
_NUMBER_CHARS = _DIGITS + b"-.eE+"

class StreamingJsonParser:
    """
    A streaming JSON parser that processes byte-based input incrementally.
    It can handle partial JSON objects and incomplete string values,
    returning the currently parsed data structure at any point.
    This version replaces the original BSON-style parser in this module.
    """

    def __init__(self):
        """Initializes the streaming JSON parser."""
        self._buffer = bytearray()
        self._result: Dict[str, Any] = {}
        self._state = _ST_EXPECT_OBJ_START

        self._current_key_bytes = bytearray()
        self._current_value_bytes = bytearray()
        
        self._active_key: Optional[str] = None # Stores the decoded string of the last fully parsed key
        self._idx = 0 # Current parsing index within self._buffer

    def consume(self, buffer: str) -> None:
        """
        Consumes a chunk of JSON data.

        Args:
            buffer: A string containing a part of the JSON document.
        """
        if not isinstance(buffer, str):
            return # Ignore invalid chunk types gracefully
        # Convert string to bytes for internal processing
        chunk = buffer.encode('utf-8')
        self._buffer.extend(chunk)
        self._process_buffer()

    def get(self) -> Dict[str, Any]:
        """
        Returns the current state of the parsed JSON object.
        This includes any fully parsed key-value pairs and partially
        completed string values if a key has been fully parsed.
        Incomplete keys are not included.

        Returns:
            A dictionary representing the currently parsed JSON object.
        """
        output_dict = self._result.copy()

        if self._active_key is not None and self._state == _ST_IN_STRING_VALUE:
            if self._current_value_bytes:
                try:
                    partial_value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                    output_dict[self._active_key] = partial_value_str
                except Exception:
                    pass 
        return output_dict

    def _handle_escape_char(self, byte_val: int) -> int:
        """Handles JSON escape sequences."""
        if byte_val == b'"'[0]: return b'"'[0]
        if byte_val == b'\\'[0]: return b'\\'[0]
        if byte_val == b'/'[0]: return b'/'[0]
        if byte_val == b'b'[0]: return b'\b'[0]
        if byte_val == b'f'[0]: return b'\f'[0]
        if byte_val == b'n'[0]: return b'\n'[0]
        if byte_val == b'r'[0]: return b'\r'[0]
        if byte_val == b't'[0]: return b'\t'[0]
        return byte_val

    def _finalize_value(self, value: Any):
        """Helper to assign a parsed value to the active key and reset."""
        if self._active_key is not None:
            self._result[self._active_key] = value
        self._active_key = None
        self._current_value_bytes.clear()
        self._state = _ST_EXPECT_COMMA_OR_OBJ_END
        
    def _parse_and_finalize_number(self):
        """Parses the number in _current_value_bytes and finalizes it."""
        if not self._current_value_bytes:
            self._state = _ST_ERROR; return False

        num_str = self._current_value_bytes.decode('utf-8') 

        if num_str == "-" or num_str == "+" or num_str.endswith(('.', 'e', 'E', '+', '-')):
            self._state = _ST_ERROR; return False

        try:
            if any(c in num_str for c in ('.', 'e', 'E')):
                parsed_num = float(num_str)
            else:
                parsed_num = int(num_str)
            self._finalize_value(parsed_num)
            return True
        except ValueError: 
            self._state = _ST_ERROR; return False

    def _process_buffer(self):
        """Processes the internal buffer to parse JSON content using a state machine."""
        buffer_len = len(self._buffer)
        while self._idx < buffer_len:
            byte = self._buffer[self._idx]

            if self._state == _ST_EXPECT_OBJ_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b'{'[0]: self._state = _ST_EXPECT_KEY_START; self._idx += 1
                else: self._state = _ST_ERROR; return 
            
            elif self._state == _ST_EXPECT_KEY_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b'"'[0]:
                    self._state = _ST_IN_KEY
                    self._current_key_bytes.clear()
                    self._active_key = None 
                    self._idx += 1
                elif byte == b'}'[0]: self._state = _ST_OBJ_END; self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_IN_KEY:
                if byte == b'\\'[0]: self._state = _ST_IN_KEY_ESCAPE; self._idx += 1
                elif byte == b'"'[0]:
                    try:
                        self._active_key = self._current_key_bytes.decode('utf-8')
                        self._state = _ST_EXPECT_COLON
                    except UnicodeDecodeError:
                        self._active_key = None; self._state = _ST_ERROR; return 
                    self._idx += 1
                else: self._current_key_bytes.append(byte); self._idx += 1
            
            elif self._state == _ST_IN_KEY_ESCAPE:
                self._current_key_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_KEY; self._idx += 1

            elif self._state == _ST_EXPECT_COLON:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b':'[0]: self._state = _ST_EXPECT_VALUE_START; self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_EXPECT_VALUE_START:
                if byte in _WHITESPACE: self._idx += 1; continue
                self._current_value_bytes.clear()
                if byte == b'"'[0]: self._state = _ST_IN_STRING_VALUE; self._idx += 1
                elif byte == b't'[0]: self._state = _ST_IN_TRUE; self._current_value_bytes.append(byte); self._idx += 1
                elif byte == b'f'[0]: self._state = _ST_IN_FALSE; self._current_value_bytes.append(byte); self._idx += 1
                elif byte == b'n'[0]: self._state = _ST_IN_NULL; self._current_value_bytes.append(byte); self._idx += 1
                elif byte in _NUMBER_CHARS and (byte != b'+'[0]): 
                    self._state = _ST_IN_NUMBER; self._current_value_bytes.append(byte); self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_IN_STRING_VALUE:
                if byte == b'\\'[0]: self._state = _ST_IN_STRING_VALUE_ESCAPE; self._idx += 1
                elif byte == b'"'[0]:
                    if self._active_key is not None:
                        try:
                            value_str = self._current_value_bytes.decode('utf-8')
                            self._finalize_value(value_str)
                        except UnicodeDecodeError: 
                            value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                            self._finalize_value(value_str)
                    else: 
                        self._state = _ST_ERROR; return
                    self._idx += 1
                else: self._current_value_bytes.append(byte); self._idx += 1

            elif self._state == _ST_IN_STRING_VALUE_ESCAPE:
                self._current_value_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_STRING_VALUE; self._idx += 1
            
            elif self._state == _ST_IN_TRUE:
                self._current_value_bytes.append(byte); self._idx += 1
                if self._current_value_bytes == b"true": self._finalize_value(True)
                elif not b"true".startswith(self._current_value_bytes): self._state = _ST_ERROR; return
            
            elif self._state == _ST_IN_FALSE:
                self._current_value_bytes.append(byte); self._idx += 1
                if self._current_value_bytes == b"false": self._finalize_value(False)
                elif not b"false".startswith(self._current_value_bytes): self._state = _ST_ERROR; return

            elif self._state == _ST_IN_NULL:
                self._current_value_bytes.append(byte); self._idx += 1
                if self._current_value_bytes == b"null": self._finalize_value(None)
                elif not b"null".startswith(self._current_value_bytes): self._state = _ST_ERROR; return
            
            elif self._state == _ST_IN_NUMBER:
                if byte in _NUMBER_CHARS: 
                    self._current_value_bytes.append(byte); self._idx += 1
                else: 
                    if not self._parse_and_finalize_number(): return 
            
            elif self._state == _ST_EXPECT_COMMA_OR_OBJ_END:
                if byte in _WHITESPACE: self._idx += 1; continue
                if byte == b','[0]: self._state = _ST_EXPECT_KEY_START; self._idx += 1
                elif byte == b'}'[0]: self._state = _ST_OBJ_END; self._idx += 1
                else: self._state = _ST_ERROR; return 

            elif self._state == _ST_OBJ_END:
                if byte in _WHITESPACE: self._idx += 1; continue 
                self._state = _ST_ERROR; return 

            elif self._state == _ST_ERROR:
                return 

            else: 
                self._state = _ST_ERROR; return
        
        if self._idx > 0:
            self._buffer = self._buffer[self._idx:]
            self._idx = 0

# --- End of Refactored StreamingJsonParser ---

# --- Original BSON-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class ParserState: # Original class
    """Immutable state container for the BSON parser."""
    buffer: str = ""; parsed_data: Dict[str, Any] = field(default_factory=dict)

class DocumentValidator:
    """Stateless validator for BSON-style documents."""
    @staticmethod
    def is_valid_key(key: Any) -> bool: return isinstance(key, str) and len(key) > 0
    @staticmethod
    def is_valid_value(value: Any) -> bool:
        if value is None or isinstance(value, (str, int, float, bool)): return True
        if isinstance(value, list): return all(DocumentValidator.is_valid_value(item) for item in value)
        if isinstance(value, dict):
            return all(isinstance(k, str) and DocumentValidator.is_valid_value(v) for k, v in value.items())
        return False
    @staticmethod
    def contains_json_structure(doc_str: str) -> bool: return "{" in doc_str

class PairExtractor: # Original class
    """Extracts complete key-value pairs from objects using stateless operations."""
    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(obj, dict): return {}
        return {key: value for key, value in obj.items()
                if DocumentValidator.is_valid_key(key) and DocumentValidator.is_valid_value(value)}

class BinaryProcessor: # Original class
    """Stateless utility for BSON-style binary processing."""
    @staticmethod
    def convert_to_binary(buffer: str) -> bytearray: return bytearray(buffer.encode("utf-8"))
    @staticmethod
    def try_read_length(buffer: bytearray, position: int) -> Optional[int]:
        if len(buffer) - position < 4: return None
        try: length_bytes = buffer[position : position + 4]; return struct.unpack("<I", length_bytes)[0]
        except struct.error: return None
    @staticmethod
    def safe_decode_binary(doc_bytes: bytearray) -> str: return doc_bytes.decode("utf-8", errors="replace")

class DocumentExtractor: # Original class
    """Extracts JSON documents using BSON-inspired parsing."""
    @staticmethod
    def extract_documents(text: str) -> list[str]:
        documents = []; current_doc = ""; brace_count = 0; in_string = False; escape_next = False
        for char in text:
            current_doc += char
            if escape_next: escape_next = False; continue
            if char == "\\": escape_next = True; continue
            if DocumentExtractor._is_string_delimiter(char, escape_next): in_string = not in_string; continue
            if not in_string:
                brace_count = DocumentExtractor._update_brace_count(char, brace_count)
                if brace_count == 0 and current_doc.strip():
                    documents.append(current_doc.strip()); current_doc = ""
        if current_doc.strip() and brace_count > 0: documents.append(current_doc.strip())
        return documents
    @staticmethod
    def _is_string_delimiter(char: str, escape_next: bool) -> bool: return char == '"' and not escape_next
    @staticmethod
    def _update_brace_count(char: str, count: int) -> int:
        if char == "{": return count + 1
        elif char == "}": return count - 1
        return count

class DocumentFormatter: # Original class
    """Stateless utility for document formatting."""
    @staticmethod
    def balance_braces(doc_str: str) -> Optional[str]:
        if not DocumentValidator.contains_json_structure(doc_str): return None
        open_braces = doc_str.count("{"); close_braces = doc_str.count("}")
        if open_braces > close_braces: return doc_str + "}" * (open_braces - close_braces)
        elif open_braces == close_braces and open_braces > 0: return doc_str
        return None

class DocumentParser: # Original class
    """Parses individual BSON-style documents."""
    def __init__(self, pair_extractor: PairExtractor = None):
        self._pair_extractor = pair_extractor or PairExtractor()
    def parse_document(self, doc_str: str) -> Dict[str, Any]:
        parsed_obj = self._try_direct_parse(doc_str)
        if parsed_obj: return self._pair_extractor.extract_complete_pairs(parsed_obj)
        return self._try_partial_parse(doc_str)
    @staticmethod
    def _try_direct_parse(doc_str: str) -> Optional[Dict[str, Any]]:
        try: obj = json.loads(doc_str); return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError: return None
    def _try_partial_parse(self, doc_str: str) -> Dict[str, Any]:
        balanced_doc = DocumentFormatter.balance_braces(doc_str)
        if not balanced_doc: return {}
        try:
            obj = json.loads(balanced_doc)
            if isinstance(obj, dict): return self._pair_extractor.extract_complete_pairs(obj)
        except json.JSONDecodeError: pass
        return {}

class BsonStyleProcessor: # Original class
    """Main processor using BSON-inspired document processing with dependency injection."""
    def __init__(self, binary_processor: BinaryProcessor = None, document_extractor: DocumentExtractor = None,
                 document_parser: DocumentParser = None):
        self._binary_processor = binary_processor or BinaryProcessor()
        self._document_extractor = document_extractor or DocumentExtractor()
        self._document_parser = document_parser or DocumentParser()
        self._binary_buffer = bytearray(); self._current_position = 0; self._document_length = None

    def process_buffer(self, buffer: str) -> Dict[str, Any]: # Original took str
        """Process buffer using BSON-inspired document structure."""
        # This method is part of the original structure and is no longer directly
        # called by the refactored StreamingJsonParser.
        self._add_to_binary_buffer(buffer)
        return self._parse_bson_style()

    def _add_to_binary_buffer(self, buffer: str) -> None:
        buffer_bytes = self._binary_processor.convert_to_binary(buffer)
        self._binary_buffer.extend(buffer_bytes)

    def _parse_bson_style(self) -> Dict[str, Any]:
        parsed_data = {}
        while self._has_remaining_data():
            if not self._try_read_document_length():
                fallback_data = self._parse_json_documents(); parsed_data.update(fallback_data); break
            if not self._try_process_document(): break
            doc_data = self._process_current_document(); parsed_data.update(doc_data)
        return parsed_data
    def _has_remaining_data(self) -> bool: return self._current_position < len(self._binary_buffer)
    def _try_read_document_length(self) -> bool:
        if self._document_length is not None: return True
        length = self._binary_processor.try_read_length(self._binary_buffer, self._current_position)
        if length is not None: self._document_length = length; self._current_position += 4; return True
        return False
    def _try_process_document(self) -> bool:
        if self._document_length is None: return True
        remaining_bytes = len(self._binary_buffer) - self._current_position
        required_bytes = self._document_length - 4
        return remaining_bytes >= required_bytes
    def _process_current_document(self) -> Dict[str, Any]:
        if self._document_length is None: return {}
        doc_size = self._document_length - 4
        doc_bytes = self._binary_buffer[self._current_position : self._current_position + doc_size]
        self._current_position += doc_size
        doc_str = self._binary_processor.safe_decode_binary(doc_bytes)
        result = self._document_parser.parse_document(doc_str)
        self._document_length = None
        return result
    def _parse_json_documents(self) -> Dict[str, Any]:
        try:
            remaining_str = self._get_remaining_string()
            documents = self._document_extractor.extract_documents(remaining_str)
            parsed_data = {}
            for doc in documents: doc_data = self._document_parser.parse_document(doc); parsed_data.update(doc_data)
            self._clear_processed_data()
            return parsed_data
        except ValueError: return {}
    def _get_remaining_string(self) -> str:
        remaining_bytes = self._binary_buffer[self._current_position :]
        return self._binary_processor.safe_decode_binary(remaining_bytes)
    def _clear_processed_data(self) -> None:
        self._binary_buffer.clear(); self._current_position = 0

# Mandatory tests for the refactored StreamingJsonParser
def test_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}')
    assert parser.get() == {"foo": "bar"}

def test_chunked_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": ')
    parser.consume('"bar"}')
    assert parser.get() == {"foo": "bar"}

def test_partial_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar')
    assert parser.get() == {"foo": "bar"}

if __name__ == '__main__':
    test_streaming_json_parser()
    test_chunked_streaming_json_parser()
    test_partial_streaming_json_parser()
    print("Refactored StreamingJsonParser tests passed successfully!")
