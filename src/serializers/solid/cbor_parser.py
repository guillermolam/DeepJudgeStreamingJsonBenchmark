import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

@dataclass(frozen=True)
class CborToken:
    """Represents a CBOR-inspired token."""
    major_type: Union[int, str]
    value: Any
    raw: str


class _TokenizeState:
    __slots__ = ('in_string', 'escape')

    def __init__(self):
        self.in_string = False
        self.escape = False

class CborTokenizer:
    """Tokenizes JSON text into CBOR-style tokens."""

    @staticmethod
    def tokenize(buffer: str) -> List[CborToken]:
        tokens: List[CborToken] = []
        current: List[str] = []
        state = _TokenizeState()
        for ch in buffer:
            if state.escape:
                current.append(ch)
                state.escape = False
                continue
            if ch == '\\':
                current.append(ch)
                state.escape = True
                continue
            if state.in_string:
                current.append(ch)
                if ch == '"' and not state.escape:
                    state.in_string = False
                    tokens.append(CborTokenizer._classify(''.join(current)))
                    current.clear()
                continue
            if ch == '"':
                current.append(ch)
                state.in_string = True
                continue
            if ch in '{}[],: \n\r\t':
                CborTokenizer._flush_current(current, tokens)
                if ch in '{}[],:':
                    tokens.append(CborToken('structural', ch, ch))
            else:
                current.append(ch)
        CborTokenizer._flush_current(current, tokens)
        return tokens

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

class CborProcessor:
    """Processes CBOR-style tokens into JSON objects with partial support."""

    @staticmethod
    def process(tokens: List[CborToken]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for start in CborProcessor._map_starts(tokens):
            end = CborProcessor._find_map_end(tokens, start)
            if end >= start:
                segment = tokens[start:end + 1]
                obj = CborProcessor._parse_segment(segment)
                if obj:
                    result.update(obj)
            else:
                # Partial map: extract whatever pairs we can
                segment = tokens[start:]
                partial = CborProcessor._partial_parse(segment)
                if partial:
                    result.update(partial)
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
        s = ''.join(
            t.raw if t.raw in '{}[],: ' else CborProcessor._value_literal(t)
            for t in segment
        )
        s = CborProcessor._repair_json(s)
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return CborProcessor._partial_parse(segment)

    @staticmethod
    def _value_literal(token: CborToken) -> str:
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
    def _partial_parse(tokens: List[CborToken]) -> Optional[Dict[str, Any]]:
        result: Dict[str, Any] = {}
        i = 1  # skip opening '{'
        while i < len(tokens):
            t = tokens[i]
            if t.major_type == 3:
                key = t.value
                i += 1
                if i < len(tokens) and tokens[i].value == ':':
                    i += 1
                    if i < len(tokens):
                        val_tok = tokens[i]
                        if val_tok.value == '{':
                            # nested partial object
                            nested = CborProcessor._partial_parse(tokens[i:]) or {}
                            result[key] = nested
                        else:
                            result[key] = val_tok.value
                        i += 1
                        if i < len(tokens) and tokens[i].value == ',':
                            i += 1
                        continue
            i += 1
        return result or None

class StreamingJsonParser:
    """CBOR-inspired streaming JSON parser supporting partial fragments."""

    def __init__(self):
        self._buffer: str = ''
        self._data: Dict[str, Any] = {}

    def consume(self, buffer: str) -> None:
        """
        Consume a JSON text chunk and update parsed data, including partial values.
        """
        self._buffer += buffer
        tokens = CborTokenizer.tokenize(self._buffer)
        pairs = CborProcessor.process(tokens)
        self._data.update(pairs)

    def get(self) -> Dict[str, Any]:
        """
        Return all parsed key-value pairs, complete or partial.
        """
        return dict(self._data)
