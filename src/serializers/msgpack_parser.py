"""
MsgPack streaming parser implementation.
Note: MsgPack is a binary format, so this implements JSON parsing
with MsgPack-inspired compact binary encoding and streaming concepts.
"""
import json
from enum import Enum
from typing import Any, Dict, Optional, List


class MsgPackFormatCode(Enum):
    """MsgPack format codes (simplified)."""
    FIXMAP = 0x80      # 1000xxxx
    FIXARRAY = 0x90    # 1001xxxx
    FIXSTR = 0xa0      # 101xxxxx
    NIL = 0xc0         # 11000000
    FALSE = 0xc2       # 11000010
    TRUE = 0xc3        # 11000011
    FLOAT32 = 0xca     # 11001010
    FLOAT64 = 0xcb     # 11001011
    UINT8 = 0xcc       # 11001100
    UINT16 = 0xcd      # 11001101
    UINT32 = 0xce      # 11001110
    UINT64 = 0xcf      # 11001111



    class MessageExtractor:
        """Extracts MsgPack-style messages from text data."""

        def extract_messages(self, text_data: str) -> List[str]:
            """Extract MsgPack-style messages from text data."""
            messages = []
            current_message = ""
            parser_state = self._create_parser_state()

            for char in text_data:
                current_message += char

                if self._should_skip_char(parser_state, char):
                    continue

                self._update_string_state(parser_state, char)

                if not parser_state['in_string']:
                    brace_count_changed = self._update_brace_count(parser_state, char)
                    if brace_count_changed and self._is_complete_message(parser_state, current_message):
                        messages.append(current_message.strip())
                        current_message = ""

            self._handle_incomplete_message(messages, current_message, parser_state)
            return messages

        @staticmethod
        def _create_parser_state() -> Dict[str, Any]:
            """Create initial parser state."""
            return {
                'brace_count': 0,
                'in_string': False,
                'escape_next': False
            }

        @staticmethod
        def _should_skip_char(parser_state: Dict[str, Any], char: str) -> bool:
            """Check if character should be skipped due to escape sequence."""
            if parser_state['escape_next']:
                parser_state['escape_next'] = False
                return True

            if char == '\\':
                parser_state['escape_next'] = True
                return True

            return False

        @staticmethod
        def _update_string_state(parser_state: Dict[str, Any], char: str) -> None:
            """Update string parsing state."""
            if char == '"' and not parser_state['escape_next']:
                parser_state['in_string'] = not parser_state['in_string']

        @staticmethod
        def _update_brace_count(parser_state: Dict[str, Any], char: str) -> bool:
            """Update brace count and return True if count changed."""
            if char == '{':
                parser_state['brace_count'] += 1
                return True
            elif char == '}':
                parser_state['brace_count'] -= 1
                return True
            return False

        @staticmethod
        def _is_complete_message(parser_state: Dict[str, Any], message: str) -> bool:
            """Check if message is complete."""
            return parser_state['brace_count'] == 0 and message.strip()

        @staticmethod
        def _handle_incomplete_message(messages: List[str], current_message: str,
                                       parser_state: Dict[str, Any]) -> None:
            """Handle incomplete message at end of input."""
            if current_message.strip() and parser_state['brace_count'] > 0:
                messages.append(current_message.strip())


class FormatCorrector:
    """Corrects message format using MsgPack-inspired rules."""
    
    def correct_format(self, message: str) -> Optional[str]:
        """Correct message format using MsgPack-inspired rules."""
        try:
            open_braces = message.count('{')
            close_braces = message.count('}')
            
            if open_braces > close_braces:
                # Add missing closing braces (MsgPack containers must be complete)
                corrected = message + '}' * (open_braces - close_braces)
                return corrected
            elif open_braces == close_braces and open_braces > 0:
                return message
            
            return None
        
        except Exception:
            return None


class ValueParser:
    """Parses values using MsgPack-inspired type detection."""
    
    def parse_value(self, value_str: str) -> Any:
        """Parse value using MsgPack-inspired type detection."""
        try:
            value_str = value_str.rstrip(',}')  # Remove trailing punctuation
            
            # MsgPack type detection
            if self._is_string(value_str):
                return self._parse_string(value_str)
            elif self._is_boolean_true(value_str):
                return True
            elif self._is_boolean_false(value_str):
                return False
            elif self._is_null(value_str):
                return None
            elif self._is_positive_integer(value_str):
                return int(value_str)
            elif self._is_negative_integer(value_str):
                return int(value_str)
            elif self._is_float(value_str):
                return self._parse_float(value_str)
            else:
                return value_str
        
        except Exception:
            return None
    
    def _is_string(self, value_str: str) -> bool:
        """Check if value is a string (fixstr in MsgPack)."""
        return value_str.startswith('"') and value_str.endswith('"')
    
    def _parse_string(self, value_str: str) -> str:
        """Parse string value."""
        return value_str[1:-1]
    
    def _is_boolean_true(self, value_str: str) -> bool:
        """Check if value is boolean true."""
        return value_str.lower() == 'true'
    
    def _is_boolean_false(self, value_str: str) -> bool:
        """Check if value is boolean false."""
        return value_str.lower() == 'false'
    
    def _is_null(self, value_str: str) -> bool:
        """Check if value is null (nil in MsgPack)."""
        return value_str.lower() == 'null'
    
    def _is_positive_integer(self, value_str: str) -> bool:
        """Check if value is a positive integer (uint in MsgPack)."""
        return value_str.isdigit()
    
    def _is_negative_integer(self, value_str: str) -> bool:
        """Check if value is a negative integer."""
        return value_str.startswith('-') and value_str[1:].isdigit()
    
    def _is_float(self, value_str: str) -> bool:
        """Check if value is a float."""
        return '.' in value_str
    
    def _parse_float(self, value_str: str) -> float:
        """Parse float value."""
        try:
            return float(value_str)
        except ValueError:
            return 0.0


class FieldExtractor:
    """Extracts fields using MsgPack-style field parsing."""
    
    def __init__(self, value_parser: ValueParser):
        self._value_parser = value_parser
    
    def extract_fields(self, message: str) -> Dict[str, Any]:
        """Extract fields using MsgPack-style field parsing."""
        try:
            result = {}
            lines = message.split('\n')
            
            for line in lines:
                line = line.strip()
                if self._is_valid_field_line(line):
                    key_value_pair = self._extract_key_value_pair(line)
                    if key_value_pair:
                        key, value = key_value_pair
                        result[key] = value
            
            return result
        
        except Exception:
            return {}
    
    def _is_valid_field_line(self, line: str) -> bool:
        """Check if line contains a valid field."""
        return ':' in line and '"' in line
    
    def _extract_key_value_pair(self, line: str) -> Optional[tuple]:
        """Extract key-value pair from a line."""
        try:
            colon_pos = line.find(':')
            if colon_pos <= 0:
                return None
            
            key_part = line[:colon_pos].strip()
            value_part = line[colon_pos + 1:].strip()
            
            # Extract key
            if not (key_part.startswith('"') and key_part.endswith('"')):
                return None
            
            key = key_part[1:-1]
            value = self._value_parser.parse_value(value_part)
            
            if value is not None:
                return key, value
            
            return None
        
        except Exception:
            return None


class PairValidator:
    """Validates key-value pairs with MsgPack-style validation."""
    
    def extract_complete_pairs(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete key-value pairs with MsgPack-style validation."""
        complete_pairs = {}
        
        for key, value in obj.items():
            if self._is_valid_key(key) and self._is_valid_value(value):
                complete_pairs[key] = value
        
        return complete_pairs
    
    def _is_valid_key(self, key: str) -> bool:
        """Check if key is valid for MsgPack encoding."""
        return isinstance(key, str) and len(key) > 0
    
    def _is_valid_value(self, value: Any) -> bool:
        """Check if value is valid for MsgPack encoding."""
        # MsgPack supports: nil, bool, int, float, str, bin, array, map, ext
        if value is None:
            return True
        if isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, list):
            return all(self._is_valid_value(item) for item in value)
        if isinstance(value, dict):
            return all(isinstance(k, str) and self._is_valid_value(v)
                      for k, v in value.items())
        
        return False


class MessageProcessor:
    """Processes MsgPack-style messages."""
    
    def __init__(self):
        self._format_corrector = FormatCorrector()
        self._value_parser = ValueParser()
        self._field_extractor = FieldExtractor(self._value_parser)
        self._pair_validator = PairValidator()
    
    def process_messages(self, messages: List[str]) -> Dict[str, Any]:
        """Process messages using MsgPack-inspired format detection."""
        parsed_data = {}
        
        for message in messages:
            message_data = self._decode_message(message)
            if message_data:
                parsed_data.update(message_data)
        
        return parsed_data
    
    def _decode_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Decode MsgPack-style message."""
        try:
            # Try direct JSON parsing first
            obj = json.loads(message)
            if isinstance(obj, dict):
                return self._pair_validator.extract_complete_pairs(obj)
        
        except json.JSONDecodeError:
            # Try MsgPack-style partial decoding
            return self._decode_partial_message(message)
        
        return None
    
    def _decode_partial_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Decode partial MsgPack message."""
        try:
            if '{' not in message:
                return None
            
            # Detect format type (map in MsgPack terms)
            corrected_message = self._format_corrector.correct_format(message)
            
            if corrected_message:
                try:
                    obj = json.loads(corrected_message)
                    if isinstance(obj, dict):
                        return self._pair_validator.extract_complete_pairs(obj)
                except json.JSONDecodeError:
                    # Try field-by-field extraction
                    return self._field_extractor.extract_fields(message)
            
            return None
        
        except Exception:
            return None


class BinaryStreamProcessor:
    """Processes binary stream for MsgPack-style processing."""
    
    def __init__(self, message_extractor: MessageExtractor, message_processor: MessageProcessor):
        self._message_extractor = message_extractor
        self._message_processor = message_processor
        self._binary_stream = bytearray()
        self._format_codes = {code.value: code.name for code in MsgPackFormatCode}
    
    def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Process buffer using MsgPack-style processing."""
        # Convert to binary stream for MsgPack-style processing
        buffer_bytes = buffer.encode('utf-8')
        self._binary_stream.extend(buffer_bytes)
        
        return self._parse_msgpack_style()
    
    def _parse_msgpack_style(self) -> Dict[str, Any]:
        """Parse using MsgPack-inspired compact encoding."""
        try:
            # Convert binary stream back to text for JSON processing
            text_data = self._binary_stream.decode('utf-8', errors='ignore')
            
            # Process as MsgPack-style messages
            messages = self._message_extractor.extract_messages(text_data)
            return self._message_processor.process_messages(messages)
        
        except Exception:
            return {}


class StreamingJsonParser:
    """Streaming JSON parser with MsgPack-inspired compact binary encoding."""
    
    def __init__(self):
        """Initialize the streaming JSON parser."""
        self._buffer = ""
        self._parsed_data = {}
        
        # Initialize components
        self._message_extractor = MessageExtractor()
        self._message_processor = MessageProcessor()
        self._binary_processor = BinaryStreamProcessor(
            self._message_extractor, 
            self._message_processor
        )
    
    def consume(self, buffer: str) -> None:
        """
        Process a chunk of JSON data incrementally using MsgPack-style processing.
        
        Args:
            buffer: String chunk of JSON data to process
        """
        self._buffer += buffer
        
        # Process using MsgPack-style binary stream processing
        new_data = self._binary_processor.process_buffer(buffer)
        if new_data:
            self._parsed_data.update(new_data)
    
    def get(self) -> Dict[str, Any]:
        """
        Return current parsed state as a Python object.
        
        Returns:
            Dictionary containing all complete key-value pairs parsed so far
        """
        return self._parsed_data.copy()