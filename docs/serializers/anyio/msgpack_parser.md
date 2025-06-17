# Documentation for `msgpack_parser.py`

## Metadata
- **Name:** anyio MsgPack Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** MessagePack-style streaming parser with anyio for async operations.
- **Strengths:** ['Asynchronous', 'Compact binary format']
- **Weaknesses:** ['Complex implementation', 'Dependency on anyio']
- **Best Use Case:** High-performance async applications requiring MessagePack support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class AsyncMsgPackExtractor
  AsyncMsgPackExtractor : _process_pair()
  AsyncMsgPackExtractor : extract_complete_pairs()
  class AsyncMsgPackParser
  AsyncMsgPackParser : __init__()
  AsyncMsgPackParser : _balance_braces_async()
  AsyncMsgPackParser : _try_direct_parse_async()
  AsyncMsgPackParser : _try_partial_parse_async()
  AsyncMsgPackParser : parse_document()
  class AsyncMsgPackProcessor
  AsyncMsgPackProcessor : __init__()
  AsyncMsgPackProcessor : _extract_documents_async()
  AsyncMsgPackProcessor : _extract_documents_sync()
  AsyncMsgPackProcessor : _process_document()
  AsyncMsgPackProcessor : process_buffer()
  class AsyncMsgPackValidator
  AsyncMsgPackValidator : is_valid_key()
  AsyncMsgPackValidator : is_valid_value()
  class AsyncParserState
  AsyncParserState : __eq__()
  AsyncParserState : __init__()
  AsyncParserState : __repr__()
  class StreamingJsonParser
  StreamingJsonParser : __init__()
  StreamingJsonParser : _consume_async()
  StreamingJsonParser : _get_async()
  StreamingJsonParser : consume()
  StreamingJsonParser : get()

```

## Flowchart
```mermaid
flowchart TD
  dataclass --> field
  field --> get_metadata

```

