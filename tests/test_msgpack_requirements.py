#!/usr/bin/env python3
import sys
sys.path.append('src/serializers/solid')

from msgpack_parser import StreamingJsonParser

def test_streaming_json_parser():
    """Test from CHALLENGE.md examples"""
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}')
    assert parser.get() == {"foo": "bar"}
    print("✓ Basic streaming test passed")

def test_chunked_streaming_json_parser():
    """Test from CHALLENGE.md examples"""
    parser = StreamingJsonParser()
    parser.consume('{"foo":')
    parser.consume('"bar')
    assert parser.get() == {"foo": "bar"}
    print("✓ Chunked streaming test passed")

def test_partial_streaming_json_parser():
    """Test from CHALLENGE.md examples"""
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar')
    assert parser.get() == {"foo": "bar"}
    print("✓ Partial streaming test passed")

def test_partial_key_not_returned():
    """Partial keys should NOT be returned - CHALLENGE.md requirement"""
    parser = StreamingJsonParser()
    parser.consume('{"test": "hello", "worl')
    result = parser.get()
    # Should only have "test" key, "worl" is incomplete key
    assert result == {"test": "hello"}
    assert "worl" not in result
    print("✓ Partial key not returned test passed")

def test_partial_string_values_returned():
    """Partial string values should be returned - CHALLENGE.md requirement"""
    parser = StreamingJsonParser()
    parser.consume('{"test": "hello", "country": "Switzerl')
    result = parser.get()
    # Should have both keys with partial value for "country"
    assert result == {"test": "hello", "country": "Switzerl"}
    print("✓ Partial string values returned test passed")

def test_value_type_determination():
    """Only return key-value once value type is determined"""
    parser = StreamingJsonParser()
    parser.consume('{"key1": "val1", "key2":')
    result = parser.get()
    # Should only have key1, key2 has no value type yet
    assert result == {"key1": "val1"}
    assert "key2" not in result
    print("✓ Value type determination test passed")

def check_solution():
    """Verify correctness against CHALLENGE.md requirements"""
    print("Running CHALLENGE.md compliance tests for msgpack parser...")
    test_streaming_json_parser()
    test_chunked_streaming_json_parser() 
    test_partial_streaming_json_parser()
    test_partial_key_not_returned()
    test_partial_string_values_returned()
    test_value_type_determination()
    print("🎉 All CHALLENGE.md requirements verified for msgpack parser!")

if __name__ == "__main__":
    check_solution()
