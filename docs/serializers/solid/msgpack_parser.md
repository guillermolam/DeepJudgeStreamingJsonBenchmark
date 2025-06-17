# Documentation for `msgpack_parser.py`

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class StreamingJsonParser
  StreamingJsonParser : __init__()
  StreamingJsonParser : _convert_number_token()
  StreamingJsonParser : _extract_and_store_value()
  StreamingJsonParser : _extract_key()
  StreamingJsonParser : _handle_comma_continuation()
  StreamingJsonParser : _is_object_end()
  StreamingJsonParser : _is_valid_object_start()
  StreamingJsonParser : _parse_key_value_pairs()
  StreamingJsonParser : _parse_obj()
  StreamingJsonParser : _parse_object_content()
  StreamingJsonParser : _parse_str()
  StreamingJsonParser : _parse_val()
  StreamingJsonParser : _parse_value_at_position()
  StreamingJsonParser : _process_single_key_value_pair()
  StreamingJsonParser : _should_include_value()
  StreamingJsonParser : _skip_whitespace()
  StreamingJsonParser : _try_parse_literals()
  StreamingJsonParser : _try_parse_number()
  StreamingJsonParser : _try_parse_object()
  StreamingJsonParser : _try_parse_string()
  StreamingJsonParser : consume()
  StreamingJsonParser : get()

```

## Flowchart
```mermaid
flowchart TD

```

