import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass(frozen=True)
class CborToken:
    """Represents a CBOR-inspired token."""
    major_type: Union[int, str]
    value: Any
    raw: str

class CborTokenizer:
    """Tokenizes JSON text into CBOR-style tokens."""

    @staticmethod
    def tokenize(buffer: str) -> List[CborToken]:
        tokens: List[CborToken] = []
        current = []  # type: List[str]
        state = _TokenizeState()
        for ch in buffer:
            if CborTokenizer._handle_escape(ch, current, state):
                continue
            if state.in_string:
                if CborTokenizer._process_in_string(ch, current, state):
                    tokens.append(CborTokenizer._classify(''.join(current)))
                    current.clear()
                continue
            if CborTokenizer._is_delimiter(ch):
                CborTokenizer._flush_current(current, tokens)
                if ch in '{}[],:':
                    tokens.append(CborToken('structural', ch, ch))
            else:
                current.append(ch)
        CborTokenizer._flush_current(current, tokens)
        return tokens

    @staticmethod
    def _handle_escape(ch: str, current: List[str], state: '_TokenizeState') -> bool:
        if state.escape:
            current.append(ch)
            state.escape = False
            return True
        if ch == '\\':
            current.append(ch)
            state.escape = True
            return True
        return False

    @staticmethod
    def _process_in_string(ch: str, current: List[str], state: '_TokenizeState') -> bool:
        current.append(ch)
        if ch == '"' and not state.escape:
            state.in_string = False
            return True
        return False

    @staticmethod
    def _is_delimiter(ch: str) -> bool:
        return ch in '{}[],: \n\r\t'

    @staticmethod
    def _flush_current(current: List[str], tokens: List[CborToken]) -> None:
        if not current:
            return
        token_str = ''.join(current).strip()
        current.clear()
        if token_str:
            tokens.append(CborTokenizer._classify(token_str))

    @staticmethod
    def _classify(token: str) -> CborToken:
        # String literal
        if token.startswith('"') and token.endswith('"'):
            return CborToken(3, token[1:-1], token)
        # Integer
        if re.fullmatch(r'-?\d+', token):
            val = int(token)
            mt = 0 if not token.startswith('-') else 1
            return CborToken(mt, val, token)
        # Float
        if re.fullmatch(r'-?\d+\.\d+', token):
            return CborToken(7, float(token), token)
        low = token.lower()
        if low in ('true', 'false', 'null'):
            val = {'true': True, 'false': False, 'null': None}[low]
            return CborToken(7, val, token)
        # Default: bare text
        return CborToken(3, token, token)


class _TokenizeState:
    __slots__ = ('in_string', 'escape')

    def __init__(self):
        self.in_string = False
        self.escape = False


class CborProcessor:
    """Processes CBOR-style tokens into JSON objects."""

    @staticmethod
    def process(tokens: List[CborToken]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for start in CborProcessor._map_starts(tokens):
            end = CborProcessor._find_map_end(tokens, start)
            if end == -1:
                continue
            obj = CborProcessor._parse_segment(tokens[start:end + 1])
            if obj:
                result.update(obj)
        return result

    @staticmethod
    def _map_starts(tokens: List[CborToken]) -> List[int]:
        return [i for i, t in enumerate(tokens) if t.value == '{']

    @staticmethod
    def _find_map_end(tokens: List[CborToken], start: int) -> int:
        depth = 0
        for idx in range(start, len(tokens)):
            v = tokens[idx].value
            depth += 1 if v == '{' else -1 if v == '}' else 0
            if depth == 0:
                return idx
        return -1

    @staticmethod
    def _parse_segment(segment: List[CborToken]) -> Optional[Dict[str, Any]]:
        json_str = CborProcessor._tokens_to_json(segment)
        try:
            obj = json.loads(json_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return CborProcessor._parse_partial(segment)

    @staticmethod
    def _tokens_to_json(tokens: List[CborToken]) -> str:
        parts: List[str] = []
        for t in tokens:
            if t.raw in '{}[],:':
                parts.append(t.raw)
            else:
                parts.append(CborProcessor._value_to_literal(t))
        joined = ''.join(parts)
        return CborProcessor._repair_json(joined)

    @staticmethod
    def _value_to_literal(token: CborToken) -> str:
        if token.value is None:
            return 'null'
        if isinstance(token.value, bool):
            return 'true' if token.value else 'false'
        if isinstance(token.value, str):
            return f'"{token.value}"'
        return str(token.value)

    @staticmethod
    def _repair_json(s: str) -> str:
        s = re.sub(r'"\s*"', '":"', s)
        s = re.sub(r'}\s*"', '},"', s)
        s = re.sub(r'"\s*{', '",{', s)
        return s

    @staticmethod
    def _parse_partial(tokens: List[CborToken]) -> Optional[Dict[str, Any]]:
        pairs = CborProcessor._extract_pairs(tokens)
        return pairs or None

    @staticmethod
    def _extract_pairs(tokens: List[CborToken]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        idx = 1
        while idx < len(tokens) - 1:
            key, idx = CborProcessor._extract_key(tokens, idx)
            if key is None:
                break
            value, idx = CborProcessor._extract_value(tokens, idx)
            if value is None:
                break
            result[key] = value
        return result

    @staticmethod
    def _extract_key(tokens: List[CborToken], idx: int) -> Tuple[Optional[str], int]:
        t = tokens[idx]
        if t.major_type == 3:
            key = t.value
            # skip key and following colon
            return key, idx + 2 if idx + 1 < len(tokens) and tokens[idx + 1].value == ':' else idx + 1
        return None, idx + 1

    @staticmethod
    def _extract_value(tokens: List[CborToken], idx: int) -> Tuple[Optional[Any], int]:
        if idx >= len(tokens) or tokens[idx].value in ('}', ','):
            return None, idx + 1
        val = tokens[idx].value
        idx += 1
        # skip comma
        if idx < len(tokens) and tokens[idx].value == ',':
            idx += 1
        return val, idx


class StreamingJsonParser:
    """CBOR-inspired streaming JSON parser."""

    def __init__(self):
        self._buffer: str = ''
        self._data: Dict[str, Any] = {}

    def consume(self, buffer: str) -> None:
        """
        Consume a JSON text chunk and update parsed data.
        """
        self._buffer += buffer
        tokens = CborTokenizer.tokenize(self._buffer)
        self._data.update(CborProcessor.process(tokens))

    def get(self) -> Dict[str, Any]:
        """
        Return all parsed key-value pairs.
        """
        return dict(self._data)
