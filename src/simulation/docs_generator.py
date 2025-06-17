"""
Documentation Generator Module
==============================
Main orchestrator for generating Python documentation.
Follows SOLID principles and Clean Code practices.
"""

import argparse
from pathlib import Path

from .file_discovery import find_py_files
from .markdown_generator import generate_markdown, generate_index


def main():
    """
    Main function to run the documentation generator.
    Orchestrates all modules while maintaining original CLI interface.
    """
    parser = argparse.ArgumentParser(
        description="Generate Markdown documentation for Python files."
    )
    parser.add_argument("files", nargs="+", help="File(s) or folder(s) to document")
    parser.add_argument("-o", "--output", default="docs", help="Output directory")
    parser.add_argument(
        "--max-depth", type=int, default=4, help="Max folder recursion depth"
    )
    parser.add_argument("--toc", action="store_true", help="Include table of contents")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()
    files = find_py_files(args.files, args.max_depth)

    if not files:
        print("❌ No valid Python files found.")
        return

    md_files = []
    for file_path in sorted(files):
        print(f"📄 Documenting: {file_path}")
        try:
            md = generate_markdown(file_path, output_dir, toc=args.toc)
            md_files.append(md)
        except Exception as e:
            print(f"⚠️  Skipped {file_path.name} due to error: {e}")

    generate_index(md_files, output_dir)
    print(f"\n✅ Documentation generated in: {output_dir}")


if __name__ == "__main__":
    main()
