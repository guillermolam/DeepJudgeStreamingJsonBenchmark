# Documentation for `orjson_parser.py`

## Metadata
- **Name:** anyio orjson Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** orjson-style streaming parser with anyio for async operations.
- **Strengths:** ['Asynchronous', 'High performance']
- **Weaknesses:** ['Complex implementation', 'Dependency on anyio']
- **Best Use Case:** High-performance async applications requiring orjson support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class AsyncOrjsonExtractor
  AsyncOrjsonExtractor : _process_pair()
  AsyncOrjsonExtractor : extract_complete_pairs()
  class AsyncOrjsonParser
  AsyncOrjsonParser : __init__()
  AsyncOrjsonParser : _balance_braces_async()
  AsyncOrjsonParser : _try_direct_parse_async()
  AsyncOrjsonParser : _try_partial_parse_async()
  AsyncOrjsonParser : parse_document()
  class AsyncOrjsonProcessor
  AsyncOrjsonProcessor : __init__()
  AsyncOrjsonProcessor : _extract_documents_async()
  AsyncOrjsonProcessor : _extract_documents_sync()
  AsyncOrjsonProcessor : _process_document()
  AsyncOrjsonProcessor : process_buffer()
  class AsyncOrjsonValidator
  AsyncOrjsonValidator : is_valid_key()
  AsyncOrjsonValidator : is_valid_value()
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

