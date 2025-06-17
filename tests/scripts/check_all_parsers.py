#!/usr/bin/env python3
"""
Script to check all StreamingJsonParser implementations for compilation and basic functionality.
"""

import importlib.util
import sys
from pathlib import Path


def test_parser_file(file_path):
    """Test a single parser file for compilation and basic functionality."""
    try:
        # Load the module
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check if StreamingJsonParser exists
        if not hasattr(module, "StreamingJsonParser"):
            return False, "No StreamingJsonParser class found"

        # Try to instantiate the parser
        parser_class = module.StreamingJsonParser
        parser = parser_class()

        # Check if required methods exist
        if not hasattr(parser, "consume"):
            return False, "No consume method found"
        if not hasattr(parser, "get"):
            return False, "No get method found"

        # Try basic functionality
        try:
            parser.consume('{"test": "value"}')
            result = parser.get()
            if not isinstance(result, dict):
                return False, f"get() returned {type(result)}, expected dict"
        except Exception as e:
            return False, f"Basic functionality test failed: {e}"

        return True, "OK"

    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Import/execution error: {e}"


def main():
    """Main function to test all parser files."""
    base_dir = Path("../../src/serializers")

    # Find all Python files in the serializers directories
    parser_files = []
    for subdir in ["raw", "anyio", "solid"]:
        subdir_path = base_dir / subdir
        if subdir_path.exists():
            for py_file in subdir_path.glob("*.py"):
                if py_file.name != "__init__.py":
                    parser_files.append(py_file)

    print(f"Testing {len(parser_files)} parser files...\n")

    failed_files = []
    passed_files = []

    for file_path in sorted(parser_files):
        relative_path = file_path.relative_to(Path.cwd())
        print(f"Testing {relative_path}...", end=" ")

        success, message = test_parser_file(file_path)

        if success:
            print("✅ PASS")
            passed_files.append(relative_path)
        else:
            print(f"❌ FAIL: {message}")
            failed_files.append((relative_path, message))

    print("\n\nSummary:")
    print(f"✅ Passed: {len(passed_files)}")
    print(f"❌ Failed: {len(failed_files)}")

    if failed_files:
        print("\nFailed files:")
        for file_path, error in failed_files:
            print(f"  {file_path}: {error}")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
