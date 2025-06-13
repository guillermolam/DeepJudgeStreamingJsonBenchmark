#!/usr/bin/env python3
"""
Test script to identify which parsers are working correctly
"""

import importlib
import json


def test_parser(parser_name, parser_class):
    """Test a single parser with simple JSON data_gen."""

    # Simple test data_gen
    test_data = {"name": "test", "value": 123, "active": True}
    json_str = json.dumps(test_data)
    json_bytes = json_str.encode('utf-8')

    try:
        # Test with bytes
        parser = parser_class()

        # Try feeding data_gen in chunks
        chunk_size = 10
        for i in range(0, len(json_bytes), chunk_size):
            chunk = json_bytes[i:i + chunk_size]
            parser.consume(chunk)

        result = parser.get()

        if result is not None:
            print(f"✓ {parser_name}: SUCCESS - Result type: {type(result)}")
            return True
        else:
            print(f"✗ {parser_name}: FAILED - No result returned")
            return False

    except Exception as e:
        print(f"✗ {parser_name}: FAILED - {str(e)}")
        return False


def main():
    """Test all parsers to find working ones."""

    parser_files = [
        'bson_parser', 'cbor_parser', 'flatbuffers_parser', 'json_parser',
        'marshall_parser', 'msgpack_parser', 'parquet_parser',
        'pickle_binary_mono_parser', 'pickle_binary_multi_parser',
        'protobuf_parser', 'reactivex_parser', 'ultrajson_parser'
    ]

    working_parsers = []

    print("Testing all parsers with simple JSON data_gen...")
    print("=" * 50)

    for parser_name in parser_files:
        try:
            module = importlib.import_module(parser_name)
            if hasattr(module, 'StreamingJsonParser'):
                parser_class = module.StreamingJsonParser
                if test_parser(parser_name, parser_class):
                    working_parsers.append(parser_name)
            else:
                print(f"✗ {parser_name}: No StreamingJsonParser class found")
        except Exception as e:
            print(f"✗ {parser_name}: Import failed - {str(e)}")

    print("\n" + "=" * 50)
    print(f"Working parsers: {len(working_parsers)}/{len(parser_files)}")
    print("Working parsers:", working_parsers)

    return working_parsers


if __name__ == "__main__":
    main()
