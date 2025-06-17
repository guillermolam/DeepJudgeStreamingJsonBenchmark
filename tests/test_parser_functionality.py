import importlib
import json
import pytest
from pathlib import Path

def get_parser_modules():
    # Discover all parser files
    base_dir = "src/serializers"
    parser_files = []
    for subdir in ["raw", "anyio", "solid"]:
        subdir_path = Path(base_dir) / subdir
        if subdir_path.exists():
            for py_file in subdir_path.glob("*.py"):
                if py_file.name != "__init__.py":
                    # Convert file path to module path
                    module_path = ".".join(py_file.with_suffix("").parts)
                    parser_files.append(module_path)
    return parser_files

@pytest.fixture(params=get_parser_modules())
def parser(request):
    """Fixture to import and instantiate StreamingJsonParser from each module."""
    module = importlib.import_module(request.param)
    return module.StreamingJsonParser()

def test_simple_json(parser):
    """Test a single parser with simple JSON data."""
    test_data = {"name": "test", "value": 123, "active": True}
    json_str = json.dumps(test_data)
    
    parser.consume(json_str)
    result = parser.get()
    assert result == test_data

@pytest.mark.parametrize("chunk_size", [1, 5, 10])
def test_chunked_json(parser, chunk_size):
    """Test a single parser with chunked JSON data."""
    test_data = {"name": "test", "value": 123, "active": True, "city": "New York"}
    json_str = json.dumps(test_data)
    
    for i in range(0, len(json_str), chunk_size):
        chunk = json_str[i:i + chunk_size]
        parser.consume(chunk)
    
    result = parser.get()
    # The final result might be partial depending on the chunking,
    # but it should be a subset of the original data.
    for key, value in result.items():
        assert key in test_data
        # For partial strings, we can only check the beginning
        if isinstance(value, str) and isinstance(test_data.get(key), str):
            assert test_data[key].startswith(value)
        else:
            assert value == test_data.get(key)

@pytest.mark.parametrize(
    "json_kv_pairs",
    [
        {"key" + str(i): "value" + str(i) for i in range(10)},
        {"key" + str(i): i for i in range(100)},
        {"key" + str(i): {"nested_key" + str(i): "nested_value" + str(i)} for i in range(5)},
    ],
)
def test_large_and_nested_json(parser, json_kv_pairs):
    """Test with a larger number of key-value pairs and nested objects."""
    json_str = json.dumps(json_kv_pairs)
    parser.consume(json_str)
    result = parser.get()
    assert result == json_kv_pairs
