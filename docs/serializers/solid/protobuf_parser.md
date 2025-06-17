# Documentation for `protobuf_parser.py`

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class FieldValidator
  FieldValidator : has_json_structure()
  FieldValidator : is_valid_protobuf_field()
  class JsonFallbackParser
  JsonFallbackParser : __init__()
  JsonFallbackParser : parse_json_messages()
  class JsonObjectExtractor
  JsonObjectExtractor : _process_single_segment()
  JsonObjectExtractor : _split_into_segments()
  JsonObjectExtractor : _try_direct_json_parse()
  JsonObjectExtractor : _try_field_parsing()
  JsonObjectExtractor : extract_json_objects()
  class MessageDecoder
  MessageDecoder : __init__()
  MessageDecoder : _try_partial_message_parse()
  MessageDecoder : _try_utf8_decode()
  MessageDecoder : decode_message()
  class MessageFrameParser
  MessageFrameParser : extract_message()
  MessageFrameParser : try_parse_length_prefixed()
  class PairExtractor
  PairExtractor : extract_complete_pairs()
  class ParserState
  ParserState : __eq__()
  ParserState : __init__()
  ParserState : __repr__()
  class PartialJsonExtractor
  PartialJsonExtractor : _balance_braces()
  PartialJsonExtractor : _parse_balanced_json()
  PartialJsonExtractor : extract_partial_json()
  class ProtobufStyleProcessor
  ProtobufStyleProcessor : __init__()
  ProtobufStyleProcessor : _parse_protobuf_style()
  ProtobufStyleProcessor : _process_next_message()
  ProtobufStyleProcessor : _try_fallback_parsing()
  ProtobufStyleProcessor : process_buffer()
  class StreamingJsonParser
  StreamingJsonParser : __init__()
  StreamingJsonParser : _advance_and_continue()
  StreamingJsonParser : _advance_and_transition()
  StreamingJsonParser : _convert_to_number()
  StreamingJsonParser : _finalize_key()
  StreamingJsonParser : _finalize_string_value()
  StreamingJsonParser : _finalize_value()
  StreamingJsonParser : _handle_error()
  StreamingJsonParser : _handle_escape_char()
  StreamingJsonParser : _handle_expect_colon()
  StreamingJsonParser : _handle_expect_comma_or_obj_end()
  StreamingJsonParser : _handle_expect_key_start()
  StreamingJsonParser : _handle_expect_obj_start()
  StreamingJsonParser : _handle_expect_value_start()
  StreamingJsonParser : _handle_in_false()
  StreamingJsonParser : _handle_in_key()
  StreamingJsonParser : _handle_in_key_escape()
  StreamingJsonParser : _handle_in_null()
  StreamingJsonParser : _handle_in_number()
  StreamingJsonParser : _handle_in_string_value()
  StreamingJsonParser : _handle_in_string_value_escape()
  StreamingJsonParser : _handle_in_true()
  StreamingJsonParser : _handle_literal_value()
  StreamingJsonParser : _handle_obj_end()
  StreamingJsonParser : _handle_unknown_state()
  StreamingJsonParser : _handle_whitespace_or_process()
  StreamingJsonParser : _is_invalid_number()
  StreamingJsonParser : _parse_and_finalize_number()
  StreamingJsonParser : _prepare_key_parsing()
  StreamingJsonParser : _process_buffer()
  StreamingJsonParser : _process_current_state()
  StreamingJsonParser : _reset_buffer_if_needed()
  StreamingJsonParser : _start_value_parsing()
  StreamingJsonParser : _try_convert_number()
  StreamingJsonParser : consume()
  StreamingJsonParser : get()

```

## Flowchart
```mermaid
flowchart TD
  dataclass --> field
  field --> test_chunked_streaming_json_parser
  test_chunked_streaming_json_parser --> test_partial_streaming_json_parser
  test_partial_streaming_json_parser --> test_streaming_json_parser

```

