# Documentation for `ultrajson_parser.py`

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class ByteProcessor
  ByteProcessor : convert_to_bytes()
  ByteProcessor : find_byte_position()
  ByteProcessor : safe_decode_bytes()
  class ByteValidator
  ByteValidator : is_escape_byte()
  ByteValidator : is_object_end_byte()
  ByteValidator : is_object_start_byte()
  ByteValidator : is_quote_byte()
  ByteValidator : is_valid_key()
  class ObjectBoundaryFinder
  ObjectBoundaryFinder : _find_object_end()
  ObjectBoundaryFinder : _find_object_start()
  ObjectBoundaryFinder : _is_object_complete()
  ObjectBoundaryFinder : _should_skip_byte()
  ObjectBoundaryFinder : _update_parse_state()
  ObjectBoundaryFinder : find_object_boundaries()
  class ObjectParseState
  ObjectParseState : __eq__()
  ObjectParseState : __init__()
  ObjectParseState : __repr__()
  class ObjectParser
  ObjectParser : __init__()
  ObjectParser : _calculate_brace_balance()
  ObjectParser : _extract_fields_fast()
  ObjectParser : _extract_key_value_pairs()
  ObjectParser : _extract_literal_value()
  ObjectParser : _extract_number_value()
  ObjectParser : _extract_string_value()
  ObjectParser : _extract_value_fast()
  ObjectParser : _find_next_key()
  ObjectParser : _find_value_for_key()
  ObjectParser : _skip_whitespace()
  ObjectParser : _try_balance_and_parse()
  ObjectParser : _try_partial_parse()
  ObjectParser : _try_standard_json_parse()
  ObjectParser : parse_object()
  class PairExtractor
  PairExtractor : extract_complete_pairs()
  class ParserState
  ParserState : __eq__()
  ParserState : __init__()
  ParserState : __repr__()
  class StreamingJsonParser
  StreamingJsonParser : __init__()
  StreamingJsonParser : _finalize_value()
  StreamingJsonParser : _handle_escape_char()
  StreamingJsonParser : _parse_and_finalize_number()
  StreamingJsonParser : _process_buffer()
  StreamingJsonParser : consume()
  StreamingJsonParser : get()
  class UltraFastProcessor
  UltraFastProcessor : __init__()
  UltraFastProcessor : _has_more_data()
  UltraFastProcessor : _is_complete_object()
  UltraFastProcessor : _process_complete_object()
  UltraFastProcessor : process_buffer()

```

## Flowchart
```mermaid
flowchart TD
  dataclass --> field
  field --> test_chunked_streaming_json_parser
  test_chunked_streaming_json_parser --> test_partial_streaming_json_parser
  test_partial_streaming_json_parser --> test_streaming_json_parser

```

