# Documentation for `bson_parser.py`

## Metadata
- **Name:** raw BSON Parser
- **Time Complexity:** O(n)
- **Space Complexity:** O(n)
- **Overall Complexity:** O(n) time, O(n) space
- **Description:** BSON-style streaming parser.
- **Strengths:** ['Handles binary data efficiently']
- **Weaknesses:** ['Simplified implementation']
- **Best Use Case:** Applications requiring BSON support.

## Class Diagram
```mermaid
classDiagram
  class Any
  Any : __new__()
  class StreamingJsonParser
  StreamingJsonParser : __init__()
  StreamingJsonParser : consume()
  StreamingJsonParser : get()
  StreamingJsonParser : reset_key_value_state()

```

## Flowchart
```mermaid
flowchart TD

```

