# Documentation for `pickle_parser.py`

## Metadata
- **Name:** anyio Pickle Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** Pickle-style streaming parser with anyio for async operations.
- **Strengths:** ['Asynchronous', 'Native Python object serialization']
- **Weaknesses:** ['Python-specific', 'Security concerns']
- **Best Use Case:** High-performance async applications requiring Pickle support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class AsyncParserState
  AsyncParserState : __eq__()
  AsyncParserState : __init__()
  AsyncParserState : __repr__()
  class AsyncPickleExtractor
  AsyncPickleExtractor : _process_pair()
  AsyncPickleExtractor : extract_complete_pairs()
  class AsyncPickleParser
  AsyncPickleParser : __init__()
  AsyncPickleParser : _balance_braces_async()
  AsyncPickleParser : _try_direct_parse_async()
  AsyncPickleParser : _try_partial_parse_async()
  AsyncPickleParser : parse_document()
  class AsyncPickleProcessor
  AsyncPickleProcessor : __init__()
  AsyncPickleProcessor : _extract_documents_async()
  AsyncPickleProcessor : _extract_documents_sync()
  AsyncPickleProcessor : _process_document()
  AsyncPickleProcessor : process_buffer()
  class AsyncPickleValidator
  AsyncPickleValidator : is_valid_key()
  AsyncPickleValidator : is_valid_value()
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

