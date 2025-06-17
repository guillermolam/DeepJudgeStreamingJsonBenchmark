"""
FlatBuffers streaming parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by FlatBuffers flat memory layout.
The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original FlatBuffers-inspired helper classes remain but are no longer used by StreamingJsonParser.
"""
import json
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
    This version replaces the original FlatBuffers-style parser in this module.
    """

    def __init__(self):
        """Initializes the streaming JSON parser."""
        self._buffer = bytearray()
        self._result: Dict[str, Any] = {}
        self._state = _ST_EXPECT_OBJ_START

        self._current_key_bytes = bytearray()
        self._current_value_bytes = bytearray()

        self._active_key: str | None = None
        self._idx = 0

    def consume(self, chunk: str) -> None: # Changed to accept str
        """
        Appends a chunk of JSON string to the internal buffer and processes it
        after converting to bytes.

        Args:
            chunk: A string containing a part of the JSON document.
        """
        if not isinstance(chunk, str):
            return

        byte_chunk = chunk.encode('utf-8', errors='replace')
        self._buffer.extend(byte_chunk)
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

# --- Original FlatBuffers-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass
class ParserState: # Original class
    """Immutable state container for the FlatBuffers parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


class TokenValidator:
    """Stateless validator for FlatBuffers-style tokens."""
    @staticmethod
    def is_valid_token(token: str) -> bool:
        return isinstance(token, str) and len(token.strip()) > 0
    @staticmethod
    def is_structural_token(token: str) -> bool:
        return token.strip() in '{}[],:'
    @staticmethod
    def is_string_token(token: str) -> bool:
        return token.startswith('"') and token.endswith('"')


class PairExtractor: # Original class
    """Extracts complete key-value pairs from objects using stateless operations."""
    @staticmethod
    def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(obj, dict):
            return {}
        return {key: value for key, value in obj.items() if TokenValidator.is_valid_token(str(key))}


class FlatTokenizer:
    """Handles tokenization with FlatBuffers-inspired flat processing."""
    @staticmethod
    def tokenize(buffer: str) -> List[str]:
        if not buffer:
            return []
        tokenizer = TokenizerState()
        for char in buffer:
            tokenizer.process_character(char)
        tokenizer.finalize()
        return tokenizer.get_tokens()
    @staticmethod
    def _is_delimiter(char: str) -> bool:
        return char in '{}[],:\n\r\t '


class TokenizerState:
    """Handles tokenization state for FlatTokenizer."""
    def __init__(self):
        self.tokens: List[str] = []
        self.current_token: str = ""
        self.in_string: bool = False
        self.escape_next: bool = False

    def process_character(self, char: str) -> None:
        if self.escape_next:
            self._handle_escaped_char_append(char) # Renamed for clarity
            return
        if char == '\\':
            self._handle_escape_set(char) # Renamed for clarity
            return
        if char == '"':
            self._handle_quote_char(char)
            return
        if self.in_string:
            self.current_token += char
            return
        self._handle_non_string_char(char)

    def _handle_escaped_char_append(self, char: str) -> None: # Renamed
        self.current_token += char
        self.escape_next = False
    def _handle_escape_set(self, char: str) -> None: # Renamed and corrected logic
        self.current_token += char
        self.escape_next = True
    def _handle_quote_char(self, char: str) -> None:
        self.current_token += char
        self.in_string = not self.in_string
    def _handle_non_string_char(self, char: str) -> None:
        if FlatTokenizer._is_delimiter(char):
            self._handle_delimiter(char)
        else:
            self.current_token += char

    def _handle_delimiter(self, char: str) -> None:
        if self.current_token.strip():
            self.tokens.append(self.current_token.strip())
            self.current_token = ""
        if char.strip() and char in '{}[],:': # Added colon
            self.tokens.append(char)

    def finalize(self) -> None:
        if self.current_token.strip():
            self.tokens.append(self.current_token.strip())
    def get_tokens(self) -> List[str]:
        return self.tokens


class ObjectBoundaryFinder: # Original class
    """Finds object boundaries in flat token arrays."""
    @staticmethod
    def find_object_boundaries(tokens: List[str]) -> List[tuple]:
        boundaries: List[tuple] = []
        i = 0
        while i < len(tokens):
            if tokens[i] == '{':
                end_pos = ObjectBoundaryFinder._find_matching_brace(tokens, i)
                if end_pos > i:
                    boundaries.append((i, end_pos))
                    i = end_pos + 1
                else:
                    i += 1
            else:
                i += 1
        return boundaries

    @staticmethod
    def _find_matching_brace(tokens: List[str], start: int) -> int:
        brace_count = 0
        for i in range(start, len(tokens)):
            token = tokens[i]
            if token == '{':
                brace_count += 1
            elif token == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
        return -1


class ObjectReconstructor:
    """Reconstructs JSON objects from flat token sequences."""
    @staticmethod
    def reconstruct_object(tokens: List[str], start: int, end: int) -> Optional[Dict[str, Any]]:
        if start >= end or start < 0 or end >= len(tokens):
            return None
        obj_tokens = tokens[start:end + 1]
        # More robust JSON string building needed here
        # This simple join might not be enough
        json_str = "".join(obj_tokens) # Simplified, likely incorrect for robust parsing
        return ObjectReconstructor._parse_json_string(json_str)

    @staticmethod
    def _build_json_string(tokens: List[str]) -> str: # Kept for original structure, but not ideal
        if not tokens:
            return ""
        return "".join(tokens)

    @staticmethod
    def _parse_json_string(json_str: str) -> Optional[Dict[str, Any]]:
        try:
            obj = json.loads(json_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return ObjectReconstructor._try_partial_parse(json_str)

    @staticmethod
    def _try_partial_parse(json_str: str) -> Optional[Dict[str, Any]]:
        if '{' not in json_str:
            return None
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        if open_braces > close_braces:
            balanced_str = json_str + '}' * (open_braces - close_braces)
            try:
                obj = json.loads(balanced_str)
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                pass
        return None


class FlatBufferProcessor: # Original class
    """Main processor using FlatBuffers-inspired flat memory layout with dependency injection."""
    def __init__(self, tokenizer: FlatTokenizer = None, boundary_finder: ObjectBoundaryFinder = None,
                 reconstructor: ObjectReconstructor = None, pair_extractor: PairExtractor = None):
        self._tokenizer = tokenizer or FlatTokenizer()
        self._boundary_finder = boundary_finder or ObjectBoundaryFinder()
        self._reconstructor = reconstructor or ObjectReconstructor()
        self._pair_extractor = pair_extractor or PairExtractor()

    def process_buffer(self, buffer: str) -> Dict[str, Any]: # Original took str
        """Process buffer using flat memory layout approach."""
        tokens = self._tokenizer.tokenize(buffer)
        if not tokens:
            return {}
        boundaries = self._boundary_finder.find_object_boundaries(tokens)
        parsed_data = {}
        for start, end in boundaries:
            obj = self._reconstructor.reconstruct_object(tokens, start, end)
            if obj:
                complete_pairs = self._pair_extractor.extract_complete_pairs(obj)
                parsed_data.update(complete_pairs)
        return parsed_data

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
    test_streaming_json_parser()
    test_chunked_streaming_json_parser()
    test_partial_streaming_json_parser()
    print("Refactored StreamingJsonParser tests passed successfully!")
