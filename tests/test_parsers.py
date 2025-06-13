#!/usr/bin/env python3
"""
Quick smoke test for all streaming JSON parsers.
Tests the basic interface and incremental parsing functionality.
"""

import pytest

# Import all parser classes from the src package
from src.serializers.json_parser import StreamingJsonParser as JsonParser
from src.serializers.marshall_parser import StreamingJsonParser as MarshallParser
from src.serializers.pickle_binary_mono_parser import StreamingJsonParser as PickleMonoParser
from src.serializers.pickle_binary_multi_parser import StreamingJsonParser as PickleMultiParser
from src.serializers.reactivex_parser import StreamingJsonParser as ReactiveXParser
from src.serializers.protobuf_parser import StreamingJsonParser as ProtobufParser
from src.serializers.flatbuffers_parser import StreamingJsonParser as FlatBuffersParser
from src.serializers.bson_parser import StreamingJsonParser as BsonParser
from src.serializers.cbor_parser import StreamingJsonParser as CborParser
from src.serializers.ultrajson_parser import StreamingJsonParser as UltraJsonParser
from src.serializers.msgpack_parser import StreamingJsonParser as MsgPackParser
from src.serializers.parquet_parser import StreamingJsonParser as ParquetParser

# List of (parser class, human-readable name)
parsers = [
    (JsonParser,         "JSON Parser"),
    (MarshallParser,     "Marshall Parser"),
    (PickleMonoParser,   "Pickle Binary Mono Parser"),
    (PickleMultiParser,  "Pickle Binary Multi Parser"),
    (ReactiveXParser,    "ReactiveX Parser"),
    (ProtobufParser,     "Protobuf Parser"),
    (FlatBuffersParser,  "FlatBuffers Parser"),
    (BsonParser,         "BSON Parser"),
    (CborParser,         "CBOR Parser"),
    (UltraJsonParser,    "Ultra-JSON Parser"),
    (MsgPackParser,      "MsgPack Parser"),
    (ParquetParser,      "Parquet Parser"),
]

@pytest.mark.parametrize("parser_class,parser_name", parsers)
def test_incremental_parsing(parser_class, parser_name):
    """
    Verify that each parser can consume JSON in chunks
    and produce a complete result containing the expected keys.
    """
    parser = parser_class()

    # Chunk 1: partial JSON
    parser.consume('{"test": "hello"')
    _ = parser.get()  # intermediate result may be partial

    # Chunk 2: adds another field and starts a third
    parser.consume(', "complete": "value", "incompl')
    _ = parser.get()

    # Chunk 3: completes the JSON
    parser.consume('ete": "final"}')
    result = parser.get()

    # Validate output
    expected_keys = {"test", "complete", "incomplete"}
    assert result is not None, f"{parser_name} returned None"
    actual_keys = set(result.keys())
    missing = expected_keys - actual_keys
    assert not missing, f"{parser_name} missing keys: {missing}"
