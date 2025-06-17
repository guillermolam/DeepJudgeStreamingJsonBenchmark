import importlib
from pathlib import Path
import pytest

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

@pytest.mark.parametrize("module_path", get_parser_modules())
def test_parser_compilation(module_path):
    """
    Test that each parser module can be imported and the StreamingJsonParser class can be instantiated.
    """
    try:
        module = importlib.import_module(module_path)
        assert hasattr(module, "StreamingJsonParser"), f"No StreamingJsonParser class found in {module_path}"
        parser_class = module.StreamingJsonParser
        parser = parser_class()
        assert hasattr(parser, "consume"), f"No consume method found in {module_path}.StreamingJsonParser"
        assert hasattr(parser, "get"), f"No get method found in {module_path}.StreamingJsonParser"
    except Exception as e:
        pytest.fail(f"Failed to import or instantiate parser from {module_path}: {e}")
