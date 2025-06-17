import ast
from pathlib import Path
import pytest

def get_parser_files():
    # Discover all parser files
    base_dir = "src/serializers"
    parser_files = []
    for subdir in ["raw", "anyio", "solid"]:
        subdir_path = Path(base_dir) / subdir
        if subdir_path.exists():
            for py_file in subdir_path.glob("*.py"):
                if py_file.name != "__init__.py":
                    parser_files.append(str(py_file))
    return parser_files

@pytest.mark.parametrize("filepath", get_parser_files())
def test_python_syntax(filepath):
    """
    Validate Python syntax of a file.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source_code = f.read()
        ast.parse(source_code, filename=filepath)
    except SyntaxError as e:
        pytest.fail(f"Syntax error in {filepath}: Line {e.lineno}: {e.text.strip() if e.text else 'N/A'} - {e.msg}")
    except Exception as e:
        pytest.fail(f"Error reading or parsing {filepath}: {e}")
