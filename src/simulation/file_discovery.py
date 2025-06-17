"""
File Discovery Module
=====================
Handles file system operations and Python file discovery.
Follows SRP: Single responsibility for file system operations.
"""

from pathlib import Path
from typing import List, Set

EXCLUDED_PREFIXES = ("__", ".")


def is_valid_python_file(file_path: Path) -> bool:
    """
    Check if file is a valid Python file for documentation.
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if valid Python file, False otherwise
    """
    return (file_path.is_file() and
            file_path.suffix == ".py" and
            not file_path.name.startswith(EXCLUDED_PREFIXES))


def should_include_subpath(subpath: Path, base_path: Path, max_depth: int) -> bool:
    """
    Check if subpath should be included based on depth and naming rules.
    
    Args:
        subpath: Path to check for inclusion
        base_path: Base directory path
        max_depth: Maximum recursion depth allowed
        
    Returns:
        bool: True if subpath should be included, False otherwise
    """
    try:
        relative = subpath.relative_to(base_path)
    except ValueError:
        return False

    depth = len(relative.parts)
    return (depth <= max_depth and
            not subpath.name.startswith(EXCLUDED_PREFIXES))


def find_py_files(paths: List[str], max_depth: int) -> Set[Path]:
    """
    Find Python files in given paths with depth control.
    
    Args:
        paths: List of file or directory paths to search
        max_depth: Maximum recursion depth for directories
        
    Returns:
        Set[Path]: Set of resolved Python file paths
    """
    py_files = set()
    for path in paths:
        p = Path(path)
        if is_valid_python_file(p):
            py_files.add(p.resolve())
        elif p.is_dir():
            for subpath in p.rglob("*.py"):
                if should_include_subpath(subpath, p, max_depth):
                    py_files.add(subpath.resolve())
    return py_files
