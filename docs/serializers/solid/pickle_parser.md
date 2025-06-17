# Documentation for `pickle_parser.py`

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class BraceBalancer
  BraceBalancer : balance_string()
  BraceBalancer : count_braces()
  BraceBalancer : needs_balancing()
  class BraceCounter
  BraceCounter : is_balanced()
  BraceCounter : update_count()
  class CharacterValidator
  CharacterValidator : is_close_brace()
  CharacterValidator : is_escape_char()
  CharacterValidator : is_open_brace()
  CharacterValidator : is_quote_char()
  CharacterValidator : is_valid_key()
  class JsonValidator
  JsonValidator : has_content()
  JsonValidator : is_valid_dict()
  class ObjectBoundaryFinder
  ObjectBoundaryFinder : _find_closing_quote()
  ObjectBoundaryFinder : _starts_with_quote()
  ObjectBoundaryFinder : find_object_end()
  ObjectBoundaryFinder : find_string_end()
  class ObjectParser
  ObjectParser : __init__()
  ObjectParser : _parse_complete_object()
  ObjectParser : parse_object_at_position()
  class PairExtractor
  PairExtractor : extract_complete_pairs()
  class ParserState
  ParserState : __eq__()
  ParserState : __init__()
  ParserState : __repr__()
  class PartialParser
  PartialParser : __init__()
  PartialParser : _balance_braces()
  PartialParser : _try_parse_json()
  PartialParser : _try_parse_substring()
  PartialParser : try_partial_parse()
  class SingleThreadedProcessor
  SingleThreadedProcessor : __init__()
  SingleThreadedProcessor : _handle_open_brace()
  SingleThreadedProcessor : _handle_quote()
  SingleThreadedProcessor : _process_character()
  SingleThreadedProcessor : parse_single_threaded()
  class StreamingJsonParser
  StreamingJsonParser : __init__()
  StreamingJsonParser : _finalize_value()
  StreamingJsonParser : _handle_escape_char()
  StreamingJsonParser : _parse_and_finalize_number()
  StreamingJsonParser : _process_buffer()
  StreamingJsonParser : consume()
  StreamingJsonParser : get()
  class StringHandler
  StringHandler : __init__()
  StringHandler : handle_string_start()
  class StringState
  StringState : __delattr__()
  StringState : __eq__()
  StringState : __hash__()
  StringState : __init__()
  StringState : __repr__()
  StringState : __setattr__()
  StringState : process_char()

```

## Flowchart
```mermaid
flowchart TD
  dataclass --> field
  field --> test_chunked_streaming_json_parser
  test_chunked_streaming_json_parser --> test_partial_streaming_json_parser
  test_partial_streaming_json_parser --> test_streaming_json_parser

```

