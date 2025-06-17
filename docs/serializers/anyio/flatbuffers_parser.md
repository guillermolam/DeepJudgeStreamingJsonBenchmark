# Documentation for `flatbuffers_parser.py`

## Metadata
- **Name:** anyio FlatBuffers Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** FlatBuffers-style streaming parser with anyio for async operations.
- **Strengths:** ['Asynchronous', 'Zero-copy potential']
- **Weaknesses:** ['Complex implementation', 'Dependency on anyio']
- **Best Use Case:** High-performance async applications requiring FlatBuffers support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class AsyncFlatBuffersExtractor
  AsyncFlatBuffersExtractor : _process_pair()
  AsyncFlatBuffersExtractor : extract_complete_pairs()
  class AsyncFlatBuffersParser
  AsyncFlatBuffersParser : __init__()
  AsyncFlatBuffersParser : _balance_braces_async()
  AsyncFlatBuffersParser : _try_direct_parse_async()
  AsyncFlatBuffersParser : _try_partial_parse_async()
  AsyncFlatBuffersParser : parse_document()
  class AsyncFlatBuffersProcessor
  AsyncFlatBuffersProcessor : __init__()
  AsyncFlatBuffersProcessor : _extract_documents_async()
  AsyncFlatBuffersProcessor : _extract_documents_sync()
  AsyncFlatBuffersProcessor : _process_document()
  AsyncFlatBuffersProcessor : process_buffer()
  class AsyncFlatBuffersValidator
  AsyncFlatBuffersValidator : is_valid_key()
  AsyncFlatBuffersValidator : is_valid_value()
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

