# Documentation for `ultrajson_parser.py`

## Metadata
- **Name:** anyio ultrajson Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** ultrajson-style streaming parser with anyio for async operations.
- **Strengths:** ['Asynchronous', 'High performance']
- **Weaknesses:** ['Complex implementation', 'Dependency on anyio']
- **Best Use Case:** High-performance async applications requiring ultrajson support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class AsyncParserState
  AsyncParserState : __eq__()
  AsyncParserState : __init__()
  AsyncParserState : __repr__()
  class AsyncUltraJsonExtractor
  AsyncUltraJsonExtractor : _process_pair()
  AsyncUltraJsonExtractor : extract_complete_pairs()
  class AsyncUltraJsonParser
  AsyncUltraJsonParser : __init__()
  AsyncUltraJsonParser : _balance_braces_async()
  AsyncUltraJsonParser : _try_direct_parse_async()
  AsyncUltraJsonParser : _try_partial_parse_async()
  AsyncUltraJsonParser : parse_document()
  class AsyncUltraJsonProcessor
  AsyncUltraJsonProcessor : __init__()
  AsyncUltraJsonProcessor : _extract_documents_async()
  AsyncUltraJsonProcessor : _extract_documents_sync()
  AsyncUltraJsonProcessor : _process_document()
  AsyncUltraJsonProcessor : process_buffer()
  class AsyncUltraJsonValidator
  AsyncUltraJsonValidator : is_valid_key()
  AsyncUltraJsonValidator : is_valid_value()
  class StreamingJsonParser
  StreamingJsonParser : __init__()
  StreamingJsonParser : _finalize_value()
  StreamingJsonParser : _handle_escape_char()
  StreamingJsonParser : _parse_and_finalize_number()
  StreamingJsonParser : _process_buffer()
  StreamingJsonParser : consume()
  StreamingJsonParser : get()

```

## Flowchart
```mermaid
flowchart TD
  dataclass --> field
  field --> get_metadata
  get_metadata --> test_chunked_streaming_json_parser
  test_chunked_streaming_json_parser --> test_partial_streaming_json_parser
  test_partial_streaming_json_parser --> test_streaming_json_parser

```

