#!/usr/bin/env python3
"""
Test script to identify which parsers are working correctly
"""

import importlib
import pytest

# List all eight module names here
PARSER_MODULES = [
    "flatbuffers_parser",
    "msgpack_parser",
    "bson_parser",
    "ultrajson_parser",
    "pickle_parser",
    "protobuf_parser",
    "cbor_parser",
    "parquet_parser",
]


@pytest.fixture(params=PARSER_MODULES, ids=lambda m: m.replace("_parser", ""))
def parser(request):
    """
    Fixture to import StreamingJsonParser from each module in turn.
    """
    mod = importlib.import_module(request.param)
    return mod.StreamingJsonParser()


def test_init_empty(parser):
    """
    After init, get() should return empty dict.
    """
    assert parser.get() == {}


def test_complete_json(parser):
    """
    A single complete object should be parsed immediately.
    """
    parser.consume('{"foo": "bar"}')
    assert parser.get() == {"foo": "bar"}


def test_chunked_streaming(parser):
    """
    Parsing across multiple consume() calls.
    """
    parser.consume('{"foo": ')
    parser.consume('"bar"}')
    assert parser.get() == {"foo": "bar"}


def test_partial_string_value(parser):
    """
    Partial string values should appear in get() once started.
    """
    parser.consume('{"hello": "worl')
    assert parser.get() == {"hello": "worl"}


def test_partial_key_not_returned(parser):
    """
    Partial keys must not appear until the colon & value type are seen.
    """
    parser.consume('{"par')
    assert parser.get() == {}


def test_multiple_pairs_partial(parser):
    """
    Multiple fields, last one partial.
    """
    parser.consume('{"a": "1", "b": 2')
    # depending on implementation, "b":2 may or may not complete;
    # at minimum "a" must be present:
    result = parser.get()
    assert result.get("a") == "1"
    # if b was parsed, it must equal the integer 2
    if "b" in result:
        assert result["b"] == 2


def test_boolean_and_null(parser):
    """
    Booleans and null should be supported once complete.
    """
    parser.consume('{"t": true, "f": false, "n": null')
    result = parser.get()
    assert result.get("t") is True
    assert result.get("f") is False
    assert result.get("n") is None


def test_nested_object_complete(parser):
    """
    A nested object, complete at the end.
    """
    parser.consume('{"outer": {"inner": "value"}}')
    assert parser.get() == {"outer": {"inner": "value"}}


def test_nested_object_partial(parser):
    """
    Nested object partially streamed: inner value incomplete.
    """
    parser.consume('{"outer": {"inner": "val')
    # Should at least have the outer key with partial inner
    result = parser.get()
    assert "outer" in result and isinstance(result["outer"], dict)
    assert result["outer"].get("inner") == "val"
