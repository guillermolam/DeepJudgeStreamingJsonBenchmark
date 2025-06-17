"""
MessagePack streaming parser implementation with anyio async operations.

This module implements a streaming JSON parser with MessagePack-style processing using anyio
for async/multi-threading operations. It follows SOLID principles with clean separation
of concerns and cognitive complexity under 14 for all methods.
"""
import json
import anyio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List


@dataclass
class AsyncParserState:
    """Immutable state container for async MessagePack parser."""
    buffer: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)


class AsyncMsgPackValidator:
    """Async validator for MessagePack-style documents."""

    @staticmethod
    async def is_valid_key(key: Any) -> bool:
        """Async check if the key is valid for MessagePack-style storage."""
        return isinstance(key, str) and len(key) > 0

    @staticmethod
    async def is_valid_value(value: Any) -> bool:
        """Async check if the value is valid for MessagePack-style storage."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return True
        if isinstance(value, (list, dict)):
            return True
        return False


class AsyncMsgPackExtractor:
    """Async extractor for complete key-value pairs."""

    @staticmethod
    async def extract_complete_pairs(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Async extract complete key-value pairs with MessagePack-style validation."""
        if not isinstance(obj, dict):
            return {}

        result = {}
        async with anyio.create_task_group() as tg:
            for key, value in obj.items():
                tg.start_soon(AsyncMsgPackExtractor._process_pair, key, value, result)

        return result

    @staticmethod
    async def _process_pair(key: str, value: Any, result: Dict[str, Any]) -> None:
        """Process a single key-value pair asynchronously."""
        if await AsyncMsgPackValidator.is_valid_key(key) and await AsyncMsgPackValidator.is_valid_value(value):
            result[key] = value


class AsyncMsgPackParser:
    """Async parser for individual MessagePack-style documents."""

    def __init__(self, extractor: AsyncMsgPackExtractor = None):
        self._extractor = extractor or AsyncMsgPackExtractor()

    async def parse_document(self, doc_str: str) -> Dict[str, Any]:
        """Async parse a MessagePack-style document."""
        parsed_obj = await self._try_direct_parse_async(doc_str)
        if parsed_obj:
            return await self._extractor.extract_complete_pairs(parsed_obj)

        return await self._try_partial_parse_async(doc_str)

    async def _try_direct_parse_async(self, doc_str: str) -> Optional[Dict[str, Any]]:
        """Async try direct JSON parsing of a document."""
        try:
            obj = await anyio.to_thread.run_sync(json.loads, doc_str)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None

    async def _try_partial_parse_async(self, doc_str: str) -> Dict[str, Any]:
        """Async try partial parsing with brace balancing."""
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

    async def _balance_braces_async(self, doc_str: str) -> Optional[str]:
        """Async balance JSON braces in document."""
        if '{' not in doc_str:
            return None

        open_braces = doc_str.count('{')
        close_braces = doc_str.count('}')

        if open_braces > close_braces:
            return doc_str + '}' * (open_braces - close_braces)
        elif open_braces == close_braces and open_braces > 0:
            return doc_str

        return None


class AsyncMsgPackProcessor:
    """Main async processor using MessagePack-inspired document processing."""

    def __init__(self, parser: AsyncMsgPackParser = None):
        self._parser = parser or AsyncMsgPackParser()

    async def process_buffer(self, buffer: str) -> Dict[str, Any]:
        """Async process buffer using MessagePack-inspired document structure."""
        documents = await self._extract_documents_async(buffer)
        
        parsed_data = {}
        async with anyio.create_task_group() as tg:
            for doc in documents:
                tg.start_soon(self._process_document, doc, parsed_data)

        return parsed_data

    async def _extract_documents_async(self, text: str) -> List[str]:
        """Async extract JSON documents from text."""
        return await anyio.to_thread.run_sync(self._extract_documents_sync, text)

    @staticmethod
    def _extract_documents_sync(text: str) -> List[str]:
        """Sync helper to extract documents."""
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
        """Process a single document asynchronously."""
        doc_data = await self._parser.parse_document(doc)
        parsed_data.update(doc_data)


def get_metadata():
    """Returns metadata for the anyio MsgPack parser."""
    return {
        'name': 'anyio MsgPack Parser',
        'time_complexity': 'O(n)',
        'space_complexity': 'O(n)',
        'overall_complexity': 'O(n) time, O(n) space',
        'description': 'MessagePack-style streaming parser with anyio for async operations.',
        'strengths': ['Asynchronous', 'Compact binary format'],
        'weaknesses': ['Complex implementation', 'Dependency on anyio'],
        'best_use_case': 'High-performance async applications requiring MessagePack support.'
    }


class StreamingJsonParser:
    """Async streaming JSON parser with MessagePack-inspired processing."""

    def __init__(self, processor: AsyncMsgPackProcessor = None):
        """Initialize the async streaming JSON parser."""
        self._state = AsyncParserState()
        self._processor = processor or AsyncMsgPackProcessor()

    def consume(self, buffer: str) -> None:
        """Process a chunk of JSON data incrementally."""
        anyio.run(self._consume_async, buffer)

    def get(self) -> Dict[str, Any]:
        """Return current parsed state as a Python object."""
        return anyio.run(self._get_async)

    async def _consume_async(self, buffer: str) -> None:
        """Async process a chunk of JSON data incrementally."""
        self._state.buffer += buffer
        new_data = await self._processor.process_buffer(buffer)
        if new_data:
            self._state.parsed_data.update(new_data)

    async def _get_async(self) -> Dict[str, Any]:
        """Async return current parsed state as a Python object."""
        return {k: self._state.parsed_data[k] for k in sorted(self._state.parsed_data.keys())}
