#!/usr/bin/env python3
"""
Simple syntax validation script for parquet_parser.py
"""

import ast
import sys


def validate_syntax(filename):
    """Validate Python syntax of a file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Parse the AST to check for syntax errors
        ast.parse(source_code, filename=filename)
        print(f"✅ Syntax validation passed for {filename}")
        return True

    except SyntaxError as e:
        print(f"❌ Syntax error in {filename}:")
        print(f"   Line {e.lineno}: {e.text.strip() if e.text else 'N/A'}")
        print(f"   Error: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")
        return False


if __name__ == "__main__":
    filename = "../../src/serializers/solid/parquet_parser.py"
    if validate_syntax(filename):
        print("🎉 File compiles successfully!")
    else:
        sys.exit(1)
