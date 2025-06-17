"""
CBOR-inspired streaming JSON parser implementation with SOLID principles.

This module *previously* implemented a streaming JSON parser inspired by CBOR (Concise Binary Object Representation)
tokenization and processing. The StreamingJsonParser class below has been refactored to be a direct, byte-based
streaming JSON parser adhering to the project-wide specification.
The original CBOR-inspired helper classes remain but are no longer used by StreamingJsonParser.
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

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
    This version replaces the original CBOR-style parser in this module.
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

# --- Original CBOR-inspired helper classes (now unused by StreamingJsonParser) ---
@dataclass(frozen=True)
class CborToken:
    """Immutable representation of a CBOR-inspired token."""
    major_type: Union[int, str]; value: Any; raw: str

@dataclass
class TokenizeState: # Original class
    """Immutable state for tokenization process."""
    in_string: bool = False; escape: bool = False

class TokenClassifier:
    """Stateless utility for classifying tokens according to CBOR types."""
    @staticmethod
    def classify_token(token: str) -> CborToken:
        if TokenClassifier._is_string_literal(token): return CborToken(3, token[1:-1], token)
        numeric_result = TokenClassifier._classify_numeric(token)
        if numeric_result: return numeric_result
        literal_result = TokenClassifier._classify_literal(token)
        if literal_result: return literal_result
        return CborToken(3, token, token)
    @staticmethod
    def _is_string_literal(token: str) -> bool: return token.startswith('"') and token.endswith('"')
    @staticmethod
    def _classify_numeric(token: str) -> Optional[CborToken]:
        if re.fullmatch(r'-?\d+', token):
            val = int(token); major_type = 0 if not token.startswith('-') else 1
            return CborToken(major_type, val, token)
        if re.fullmatch(r'-?\d+\.\d+', token): return CborToken(7, float(token), token)
        return None
    @staticmethod
    def _classify_literal(token: str) -> Optional[CborToken]:
        token_lower = token.lower(); literal_map = {'true': True, 'false': False, 'null': None}
        if token_lower in literal_map: return CborToken(7, literal_map[token_lower], token)
        return None

class TokenBuffer:
    """Stateless utility for managing token buffer operations."""
    @staticmethod
    def flush_to_tokens(current: List[str], tokens: List[CborToken]) -> None:
        if not current: return
        token_str = ''.join(current).strip(); current.clear()
        if token_str: tokens.append(TokenClassifier.classify_token(token_str))
    @staticmethod
    def is_structural_char(ch: str) -> bool: return ch in '{}[],:'
    @staticmethod
    def is_whitespace(ch: str) -> bool: return ch in ' \n\r\t'

class CborTokenizer: # Original class
    """Tokenizes JSON text into CBOR-style tokens with stateless operations."""
    @staticmethod
    def tokenize(buffer: str) -> List[CborToken]:
        tokens: List[CborToken] = []; current: List[str] = []; state = TokenizeState()
        for ch in buffer: state = CborTokenizer._process_character(ch, current, tokens, state)
        TokenBuffer.flush_to_tokens(current, tokens)
        return tokens

    @staticmethod
    def _process_character(ch: str, current: List[str], tokens: List[CborToken], state: TokenizeState) -> TokenizeState:
        if state.escape: current.append(ch); return TokenizeState(state.in_string, False)
        if ch == '\\': current.append(ch); return TokenizeState(state.in_string, True)
        if state.in_string: return CborTokenizer._process_string_character(ch, current, tokens, state)
        return CborTokenizer._process_non_string_character(ch, current, tokens, state)

    @staticmethod
    def _process_string_character(ch: str, current: List[str], tokens: List[CborToken], state: TokenizeState) -> TokenizeState:
        current.append(ch)
        if ch == '"' and not state.escape:
            tokens.append(TokenClassifier.classify_token(''.join(current))); current.clear()
            return TokenizeState(False, False)
        return state

    @staticmethod
    def _process_non_string_character(ch: str, current: List[str], tokens: List[CborToken], state: TokenizeState) -> TokenizeState:
        if ch == '"': current.append(ch); return TokenizeState(True, False)
        if TokenBuffer.is_structural_char(ch) or TokenBuffer.is_whitespace(ch):
            TokenBuffer.flush_to_tokens(current, tokens)
            if TokenBuffer.is_structural_char(ch): tokens.append(CborToken('structural', ch, ch))
        else: current.append(ch)
        return state

class MapTokenProcessor:
    """Stateless utility for processing map tokens."""
    @staticmethod
    def find_map_starts(tokens: List[CborToken]) -> List[int]:
        return [i for i, token in enumerate(tokens) if token.value == '{']
    @staticmethod
    def find_map_end(tokens: List[CborToken], start: int) -> int:
        depth = 0
        for idx in range(start, len(tokens)):
            token_value = tokens[idx].value
            if token_value == '{': depth += 1
            elif token_value == '}': depth -= 1
            if depth == 0: return idx
        return -1

class JsonStringBuilder:
    """Stateless utility for building JSON strings from tokens."""
    @staticmethod
    def build_json_string(segment: List[CborToken]) -> str:
        return ''.join(token.raw if JsonStringBuilder._use_raw_token(token) else JsonStringBuilder._get_value_literal(token) for token in segment)
    @staticmethod
    def _use_raw_token(token: CborToken) -> bool: return token.raw in '{}[],: '
    @staticmethod
    def _get_value_literal(token: CborToken) -> str:
        if token.value is None: return 'null'
        if isinstance(token.value, bool): return 'true' if token.value else 'false'
        if isinstance(token.value, str): return f'"{token.value}"'
        return str(token.value)
    @staticmethod
    def repair_json_string(json_str: str) -> str:
        json_str = re.sub(r'"\s*"', '":"', json_str)
        json_str = re.sub(r'}\s*"', '},"', json_str)
        json_str = re.sub(r'"\s*{', '",{', json_str)
        return json_str

class PartialObjectParser: # Original class
    """Stateless utility for parsing partial objects from tokens."""
    @staticmethod
    def parse_partial_object(tokens: List[CborToken]) -> Optional[Dict[str, Any]]:
        result: Dict[str, Any] = {}; index = 1
        while index < len(tokens):
            parse_result = PartialObjectParser._try_parse_key_value_pair(tokens, index)
            if parse_result is None: index += 1; continue
            key, value, new_index = parse_result
            result[key] = value; index = new_index
        return result if result else None

    @staticmethod
    def _try_parse_key_value_pair(tokens: List[CborToken], index: int) -> Optional[tuple]:
        key_result = PartialObjectParser._extract_key_at_index(tokens, index)
        if key_result is None: return None
        key, colon_index = key_result
        value_result = PartialObjectParser._parse_value_at_index(tokens, colon_index + 1)
        if value_result is None: return None
        value, new_index = value_result
        if PartialObjectParser._has_comma_at_index(tokens, new_index): new_index += 1
        return key, value, new_index

    @staticmethod
    def _extract_key_at_index(tokens: List[CborToken], index: int) -> Optional[tuple]:
        if index >= len(tokens): return None
        token = tokens[index]
        if token.major_type != 3: return None
        key = token.value; colon_index = index + 1
        if not PartialObjectParser._has_colon_at_index(tokens, colon_index): return None
        return key, colon_index

    @staticmethod
    def _has_colon_at_index(tokens: List[CborToken], index: int) -> bool:
        return index < len(tokens) and tokens[index].value == ':'
    @staticmethod
    def _has_comma_at_index(tokens: List[CborToken], index: int) -> bool:
        return index < len(tokens) and tokens[index].value == ','
    @staticmethod
    def _parse_value_at_index(tokens: List[CborToken], index: int) -> Optional[tuple]:
        if index >= len(tokens): return None
        value_token = tokens[index]
        if value_token.value == '{':
            nested = PartialObjectParser.parse_partial_object(tokens[index:]) or {}
            # This logic for advancing index for nested might be too simple
            # A proper nested parser would return how many tokens it consumed.
            # For now, assume it consumes at least one '{'.
            # A more robust way would be to find the matching '}' for the nested object.
            # Simplified:
            # Find matching '}' to determine tokens consumed by nested object
            nested_end_idx = MapTokenProcessor.find_map_end(tokens, index)
            if nested_end_idx != -1:
                 return nested, nested_end_idx + 1 # Advance past the consumed nested object
            else: # Could not find end of nested, treat as error or partial
                 return nested, index + 1 # Minimal advance
        else:
            return value_token.value, index + 1

class CborProcessor: # Original class
    """Processes CBOR-style tokens into JSON objects with partial support."""
    @staticmethod
    def process(tokens: List[CborToken]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}; map_starts = MapTokenProcessor.find_map_starts(tokens)
        for start in map_starts:
            processed_object = CborProcessor._process_single_map(tokens, start)
            if processed_object: result.update(processed_object)
        return result

    @staticmethod
    def _process_single_map(tokens: List[CborToken], start: int) -> Optional[Dict[str, Any]]:
        end = MapTokenProcessor.find_map_end(tokens, start)
        if end >= start:
            segment = tokens[start:end + 1]
            return CborProcessor._parse_complete_segment(segment)
        else:
            segment = tokens[start:]
            return PartialObjectParser.parse_partial_object(segment)

    @staticmethod
    def _parse_complete_segment(segment: List[CborToken]) -> Optional[Dict[str, Any]]:
        json_string = JsonStringBuilder.build_json_string(segment)
        repaired_json = JsonStringBuilder.repair_json_string(json_string)
        try:
            obj = json.loads(repaired_json)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError: return PartialObjectParser.parse_partial_object(segment)

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
