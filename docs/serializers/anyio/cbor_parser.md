# Documentation for `cbor_parser.py`

## Metadata
- **Name:** anyio CBOR Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** CBOR-style streaming parser with anyio for async operations.
- **Strengths:** ['Asynchronous', 'Compact binary format']
- **Weaknesses:** ['Complex implementation', 'Dependency on anyio']
- **Best Use Case:** High-performance async applications requiring CBOR support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class AsyncCborExtractor
  AsyncCborExtractor : _process_pair()
  AsyncCborExtractor : extract_complete_pairs()
  class AsyncCborParser
  AsyncCborParser : __init__()
  AsyncCborParser : _balance_braces_async()
  AsyncCborParser : _extract_partial_fields_async()
  AsyncCborParser : _extract_partial_fields_sync()
  AsyncCborParser : _find_matching_brace()
  AsyncCborParser : _try_direct_parse_async()
  AsyncCborParser : _try_partial_parse_async()
  AsyncCborParser : parse_document()
  class AsyncCborProcessor
  AsyncCborProcessor : __init__()
  AsyncCborProcessor : _extract_documents_async()
  AsyncCborProcessor : _extract_documents_sync()
  AsyncCborProcessor : _process_document()
  AsyncCborProcessor : process_buffer()
  class AsyncCborValidator
  AsyncCborValidator : is_valid_key()
  AsyncCborValidator : is_valid_value()
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

