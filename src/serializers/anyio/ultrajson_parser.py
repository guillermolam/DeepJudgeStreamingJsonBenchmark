"""
Ultra-JSON streaming parser implementation with anyio async operations.

This module *previously* implemented an async streaming JSON parser with Ultra-JSON-style processing.
The StreamingJsonParser class below has been refactored to be a direct, synchronous, byte-based
streaming JSON parser adhering to the project-wide specification.
The original async helper classes remain but are no longer used by the refactored StreamingJsonParser.
"""
import json
import anyio # Retained for context, but not used by the refactored parser
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

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
    This version is synchronous and replaces the original async parser in this module.
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
            # For robustness, or if mixed types are possible, handle or raise.
            return # Or raise TypeError("consume expects str")
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
        if byte_val == b'"'[0]:
            return b'"'[0]
        if byte_val == b'\\'[0]:
            return b'\\'[0]
        if byte_val == b'/'[0]:
            return b'/'[0]
        if byte_val == b'b'[0]:
            return b'\b'[0]
        if byte_val == b'f'[0]:
            return b'\f'[0]
        if byte_val == b'n'[0]:
            return b'\n'[0]
        if byte_val == b'r'[0]:
            return b'\r'[0]
        if byte_val == b't'[0]:
            return b'\t'[0]
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
            self._state = _ST_ERROR
            return False

        num_str = self._current_value_bytes.decode('utf-8')

        if num_str == "-" or num_str == "+" or num_str.endswith(('.', 'e', 'E', '+', '-')):
            self._state = _ST_ERROR
            return False

        try:
            if any(c in num_str for c in ('.', 'e', 'E')):
                parsed_num = float(num_str)
            else:
                parsed_num = int(num_str)
            self._finalize_value(parsed_num)
            return True
        except ValueError:
            self._state = _ST_ERROR
            return False

    def _process_buffer(self):
        """Processes the internal buffer to parse JSON content using a state machine."""
        buffer_len = len(self._buffer)
        while self._idx < buffer_len:
            byte = self._buffer[self._idx]

            if self._state == _ST_EXPECT_OBJ_START:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b'{'[0]:
                    self._state = _ST_EXPECT_KEY_START
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_EXPECT_KEY_START:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b'"'[0]:
                    self._state = _ST_IN_KEY
                    self._current_key_bytes.clear()
                    self._active_key = None
                    self._idx += 1
                elif byte == b'}'[0]:
                    self._state = _ST_OBJ_END
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_KEY:
                if byte == b'\\'[0]:
                    self._state = _ST_IN_KEY_ESCAPE
                    self._idx += 1
                elif byte == b'"'[0]:
                    try:
                        self._active_key = self._current_key_bytes.decode('utf-8')
                        self._state = _ST_EXPECT_COLON
                    except UnicodeDecodeError:
                        self._active_key = None
                        self._state = _ST_ERROR
                        return
                    self._idx += 1
                else:
                    self._current_key_bytes.append(byte)
                    self._idx += 1

            elif self._state == _ST_IN_KEY_ESCAPE:
                self._current_key_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_KEY
                self._idx += 1

            elif self._state == _ST_EXPECT_COLON:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b':'[0]:
                    self._state = _ST_EXPECT_VALUE_START
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_EXPECT_VALUE_START:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                self._current_value_bytes.clear()
                if byte == b'"'[0]:
                    self._state = _ST_IN_STRING_VALUE
                    self._idx += 1
                elif byte == b't'[0]:
                    self._state = _ST_IN_TRUE
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                elif byte == b'f'[0]:
                    self._state = _ST_IN_FALSE
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                elif byte == b'n'[0]:
                    self._state = _ST_IN_NULL
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                elif byte in _NUMBER_CHARS and (byte != b'+'[0]):
                    self._state = _ST_IN_NUMBER
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_STRING_VALUE:
                if byte == b'\\'[0]:
                    self._state = _ST_IN_STRING_VALUE_ESCAPE
                    self._idx += 1
                elif byte == b'"'[0]:
                    if self._active_key is not None:
                        try:
                            value_str = self._current_value_bytes.decode('utf-8')
                            self._finalize_value(value_str)
                        except UnicodeDecodeError:
                            value_str = self._current_value_bytes.decode('utf-8', errors='replace')
                            self._finalize_value(value_str)
                    else:
                        self._state = _ST_ERROR
                        return
                    self._idx += 1
                else:
                    self._current_value_bytes.append(byte)
                    self._idx += 1

            elif self._state == _ST_IN_STRING_VALUE_ESCAPE:
                self._current_value_bytes.append(self._handle_escape_char(byte))
                self._state = _ST_IN_STRING_VALUE
                self._idx += 1

            elif self._state == _ST_IN_TRUE:
                self._current_value_bytes.append(byte)
                self._idx += 1
                if self._current_value_bytes == b"true":
                    self._finalize_value(True)
                elif not b"true".startswith(self._current_value_bytes):
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_FALSE:
                self._current_value_bytes.append(byte)
                self._idx += 1
                if self._current_value_bytes == b"false":
                    self._finalize_value(False)
                elif not b"false".startswith(self._current_value_bytes):
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_NULL:
                self._current_value_bytes.append(byte)
                self._idx += 1
                if self._current_value_bytes == b"null":
                    self._finalize_value(None)
                elif not b"null".startswith(self._current_value_bytes):
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_IN_NUMBER:
                if byte in _NUMBER_CHARS:
                    self._current_value_bytes.append(byte)
                    self._idx += 1
                else:
                    if not self._parse_and_finalize_number():
                        return

            elif self._state == _ST_EXPECT_COMMA_OR_OBJ_END:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                if byte == b','[0]:
                    self._state = _ST_EXPECT_KEY_START
                    self._idx += 1
                elif byte == b'}'[0]:
                    self._state = _ST_OBJ_END
                    self._idx += 1
                else:
                    self._state = _ST_ERROR
                    return

            elif self._state == _ST_OBJ_END:
                if byte in _WHITESPACE:
                    self._idx += 1
                    continue
                self._state = _ST_ERROR
                return

            elif self._state == _ST_ERROR:
                return

            else:
                self._state = _ST_ERROR
                return

        if self._idx > 0:
            self._buffer = self._buffer[self._idx:]
            self._idx = 0

# --- End of Refactored StreamingJsonParser ---

# --- Original Async Ultra-JSON-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class AsyncParserState: # Original class
    """Immutable state container for async Ultra-JSON parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)

class AsyncUltraJsonValidator: # Original class
    """Async validator for Ultra-JSON-style documents."""
    @staticmethod
    async def is_valid_key(key: Any) -> bool:
        return isinstance(key, str) and len(key) > 0
    @staticmethod
    async def is_valid_value(value: Any) -> bool:
        if value is None or isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, (list, dict)):
            return True
        return False

class AsyncUltraJsonExtractor: # Original class
    """Async extractor for complete key-value pairs."""
    @staticmethod
    async def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(obj, dict):
            return {}
        result = {}
        async with anyio.create_task_group() as tg:
            for key, value in obj.items():
                tg.start_soon(AsyncUltraJsonExtractor._process_pair, key, value, result)
        return result
    @staticmethod
    async def _process_pair(key: str, value: Any, result: Dict[str, Any]) -> None:
        if await AsyncUltraJsonValidator.is_valid_key(key) and await AsyncUltraJsonValidator.is_valid_value(value):
            result[key] = value

class AsyncUltraJsonParser: # Original class
    """Async parser for individual Ultra-JSON-style documents."""
    def __init__(self, extractor: AsyncUltraJsonExtractor = None):
        self._extractor = extractor or AsyncUltraJsonExtractor()
    async def parse_document(self, doc_str: str) -> Dict[str, Any]:
        parsed_obj = await self._try_direct_parse_async(doc_str)
        if parsed_obj:
            return await self._extractor.extract_complete_pairs(parsed_obj)
        return await self._try_partial_parse_async(doc_str)
    @staticmethod
    async def _try_direct_parse_async(doc_str: str) -> Optional[Dict[str, Any]]:
        try:
            obj = await anyio.to_thread.run_sync(json.loads, doc_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    async def _try_partial_parse_async(self, doc_str: str) -> Dict[str, Any]:
        balanced_doc = await self._balance_braces_async(doc_str)
        if not balanced_doc:
            return {}
        try:
            obj = await anyio.to_thread.run_sync(json.loads, balanced_doc)
            if isinstance(obj, dict):
                return await self._extractor.extract_complete_pairs(obj)
        except json.JSONDecodeError:
            pass
        return {}
    @staticmethod
    async def _balance_braces_async(doc_str: str) -> Optional[str]:
        if '{' not in doc_str:
            return None
        open_braces = doc_str.count('{')
        close_braces = doc_str.count('}')
        if open_braces > close_braces:
            return doc_str + '}' * (open_braces - close_braces)
        elif open_braces == close_braces and open_braces > 0:
            return doc_str
        return None

class AsyncUltraJsonProcessor: # Original class
    """Main async processor using Ultra-JSON-inspired document processing."""
    def __init__(self, parser: AsyncUltraJsonParser = None):
        self._parser = parser or AsyncUltraJsonParser()
    async def process_buffer(self, buffer: str) -> Dict[str, Any]:
        documents = await self._extract_documents_async(buffer)
        parsed_data = {}
        async with anyio.create_task_group() as tg:
            for doc in documents:
                tg.start_soon(self._process_document, doc, parsed_data)
        return parsed_data
    async def _extract_documents_async(self, text: str) -> List[str]:
        return await anyio.to_thread.run_sync(self._extract_documents_sync, text)
    @staticmethod
    def _extract_documents_sync(text: str) -> List[str]:
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
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and current_doc.strip():
                        documents.append(current_doc.strip())
                        current_doc = ""
        if current_doc.strip() and brace_count > 0:
            documents.append(current_doc.strip())
        return documents
    async def _process_document(self, doc: str, parsed_data: Dict[str, Any]) -> None:
        doc_data = await self._parser.parse_document(doc)
        parsed_data.update(doc_data)

# Mandatory tests for the refactored StreamingJsonParser
def test_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}') # Changed to str
    assert parser.get() == {"foo": "bar"}

def test_chunked_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": ') # Changed to str
    parser.consume('"bar"}') # Changed to str
    assert parser.get() == {"foo": "bar"}

def test_partial_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar') # Changed to str
    assert parser.get() == {"foo": "bar"}

if __name__ == '__main__':
    # Note: The original __main__ block might have used anyio.run for its tests.
    # This refactored parser is synchronous, so tests run directly.
    test_streaming_json_parser()
    test_chunked_streaming_json_parser()
    test_partial_streaming_json_parser()
    print("Refactored StreamingJsonParser tests passed successfully!")
