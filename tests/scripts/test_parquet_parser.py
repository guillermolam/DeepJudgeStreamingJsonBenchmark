#!/usr/bin/env python3
"""
Test script to verify parquet_parser.py compiles and runs correctly.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Import the module to test compilation
    from serializers.solid.parquet_parser import StreamingJsonParser
    print("✅ Module imported successfully")
    
    # Run the embedded tests
    def test_streaming_json_parser():
        parser = StreamingJsonParser()
        parser.consume(b'{"foo": "bar"}')
        assert parser.get() == {"foo": "bar"}
        print("✅ test_streaming_json_parser passed")

    def test_chunked_streaming_json_parser():
        parser = StreamingJsonParser()
        parser.consume(b'{"foo": ')
        parser.consume(b'"bar"}')
        assert parser.get() == {"foo": "bar"}
        print("✅ test_chunked_streaming_json_parser passed")

    def test_partial_streaming_json_parser():
        parser = StreamingJsonParser()
        parser.consume(b'{"foo": "bar')
        assert parser.get() == {"foo": "bar"}
        print("✅ test_partial_streaming_json_parser passed")

    # Run all tests
    test_streaming_json_parser()
    test_chunked_streaming_json_parser()
    test_partial_streaming_json_parser()
    
    print("\n🎉 All tests passed successfully!")
    print("✅ parquet_parser.py compiles and all embedded tests run successfully")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)