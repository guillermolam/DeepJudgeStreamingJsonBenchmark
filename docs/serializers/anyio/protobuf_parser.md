# Documentation for `protobuf_parser.py`

## Metadata
- **Name:** anyio Protobuf Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** Protocol Buffers-style streaming parser with anyio for async operations.
- **Strengths:** ['Asynchronous', 'Schema enforcement']
- **Weaknesses:** ['Complex implementation', 'Dependency on anyio']
- **Best Use Case:** High-performance async applications requiring Protocol Buffers support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class AsyncParserState
  AsyncParserState : __eq__()
  AsyncParserState : __init__()
  AsyncParserState : __repr__()
  class AsyncProtobufExtractor
  AsyncProtobufExtractor : _process_pair()
  AsyncProtobufExtractor : extract_complete_pairs()
  class AsyncProtobufParser
  AsyncProtobufParser : __init__()
  AsyncProtobufParser : _balance_braces_async()
  AsyncProtobufParser : _try_direct_parse_async()
  AsyncProtobufParser : _try_partial_parse_async()
  AsyncProtobufParser : parse_document()
  class AsyncProtobufProcessor
  AsyncProtobufProcessor : __init__()
  AsyncProtobufProcessor : _extract_documents_async()
  AsyncProtobufProcessor : _extract_documents_sync()
  AsyncProtobufProcessor : _process_document()
  AsyncProtobufProcessor : process_buffer()
  class AsyncProtobufValidator
  AsyncProtobufValidator : is_valid_key()
  AsyncProtobufValidator : is_valid_value()
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

