import json
import sys
from pathlib import Path

import pytest

# Add project root to sys.path to import from main
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.data_gen import (
    generate_test_data,
    create_streaming_chunks,
    validate_generated_data,
)


# Lazy import parser discovery
def get_loaded_parsers():
    try:
        from main import ParserDiscovery

        return ParserDiscovery().discover_parsers()
    except Exception:
        return {}


LOADED_PARSERS = get_loaded_parsers()


class TestDataGen:
    @pytest.mark.parametrize("num_fields", [1, 10, 100])
    def test_generate_test_data_structure(self, num_fields: int):
        data = generate_test_data(num_fields)
        assert isinstance(data, dict)
        assert "_metadata" in data
        assert data["_metadata"]["target_fields"] == num_fields

    def test_validate_field_count_within_tolerance(self):
        assert validate_generated_data(generate_test_data(100), expected_fields=100)

    def test_only_strings_or_objects_in_generated_data(self):
        def validate(obj):
            assert isinstance(obj, dict)
            for k, v in obj.items():
                assert isinstance(k, str)
                assert not isinstance(v, list)
                assert not isinstance(v, (int, float, bool, type(None)))
                if isinstance(v, dict):
                    validate(v)

        data = generate_test_data(50)
        payload_only = {k: v for k, v in data.items() if k != "_metadata"}
        validate(payload_only)

    def test_create_streaming_chunks(self):
        test_data = {"field": "value", "nested": {"x": "y"}}
        json_bytes = json.dumps(test_data).encode("utf-8")
        chunks = create_streaming_chunks(json_bytes)
        assert isinstance(chunks, list)
        assert all(isinstance(chunk, bytes) for chunk in chunks)
        assert b"".join(chunks) == json_bytes


# Conditionally define test if parsers are available
if LOADED_PARSERS:

    @pytest.mark.parametrize("parser_name, parser_class", LOADED_PARSERS.items())
    def test_parser_can_consume_and_return_data(parser_name, parser_class):
        print(
            f"parser_name={parser_name}, parser_class={parser_class}, type={type(parser_class)}"
        )

        parser = parser_class()
        test_input = '{"foo": "bar", "name": "hello", "company":"deep_judge", "chars":"%@$@#$^#%^#W#.21@" }' # Changed from bytes to str

        try:
            parser.consume(test_input)
            result = parser.get()
            assert isinstance(result, dict), f"{parser_name} did not return a dict"
            assert result.get("foo") == "bar", f"{parser_name} parsed incorrect value"
        except Exception as e:
            pytest.fail(f"{parser_name} failed with error: {e}")

else:
    pytest.skip("No parsers discovered to test.", allow_module_level=True)
