import os
import ast
import argparse
import subprocess
from pathlib import Path
from typing import List, Set
import asttokens

EXCLUDED_PREFIXES = ("__", ".")


def find_py_files(paths: List[str], max_depth: int) -> Set[Path]:
    py_files = set()
    for path in paths:
        p = Path(path)
        if p.is_file() and p.suffix == ".py" and not p.name.startswith(EXCLUDED_PREFIXES):
            py_files.add(p.resolve())
        elif p.is_dir():
            for subpath in p.rglob("*.py"):
                try:
                    relative = subpath.relative_to(p)
                except ValueError:
                    continue
                depth = len(relative.parts)
                if (
                    depth <= max_depth
                    and not subpath.name.startswith(EXCLUDED_PREFIXES)
                ):
                    py_files.add(subpath.resolve())
    return py_files


def generate_uml(file_path: Path, output_dir: Path) -> str:
    module_name = file_path.stem
    command = ["pyreverse", "-o", "png", "-p", module_name, str(file_path)]
    subprocess.run(command, check=True)
    generated_png = f"classes_{module_name}.png"
    dest = output_dir / generated_png
    if Path(generated_png).exists():
        os.rename(generated_png, dest)
        return dest.name
    return ""


def generate_flowchart(file_path: Path, output_dir: Path) -> str:
    output_png = output_dir / f"{file_path.stem}_flowchart.png"
    subprocess.run(["code2flow", str(file_path), "-o", str(output_png)], check=True)
    return output_png.name


def analyze_code(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8") as f:
        source = f.read()

    atok = asttokens.ASTTokens(source, parse=True)
    tree = atok.tree
    explanation = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            explanation.append(f"### Function `{node.name}`")
            args = [arg.arg for arg in node.args.args]
            explanation.append(f"**Arguments:** {args}")
            explanation.append(f"**Docstring:** {ast.get_docstring(node)}")
            explanation.append("**Explanation:**\nThis function likely performs...")
        elif isinstance(node, ast.ClassDef):
            explanation.append(f"## Class `{node.name}`")
            explanation.append(f"**Docstring:** {ast.get_docstring(node)}")
            explanation.append("**Explanation:**\nThis class is responsible for...")

    return "\n".join(explanation)


def generate_interview_qa(file_path: Path) -> str:
    base_name = file_path.stem
    return f"""
## Interview Q&A for `{base_name}`

**Q: What problem does this algorithm solve?**  
A: This algorithm focuses on...

**Q: What data structures are used and why?**  
A: It uses lists/dictionaries/queues because...

**Q: What is the time and space complexity?**  
A: Time complexity is O(...) and space is O(...)

**Q: Can this be optimized further?**  
A: Potential optimizations include...

**Q: What are edge cases to test?**  
A: Empty input, large input, invalid types...
"""


def generate_step_by_step(file_path: Path) -> str:
    return """
            ## Step-by-Step Execution
            1. Load and parse the input file.
            2. Construct AST and tokenize.
            3. Identify main structures (classes/functions).
            4. Extract control flow and generate diagrams.
            5. Write detailed markdown with explanation.
            """


def generate_markdown(file_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    uml_img = generate_uml(file_path, output_dir)
    flow_img = generate_flowchart(file_path, output_dir)
    analysis = analyze_code(file_path)
    q_and_a = generate_interview_qa(file_path)
    steps = generate_step_by_step(file_path)

    markdown = f"""# Documentation for `{file_path.name}`

{f"![UML Diagram](./{uml_img})" if uml_img else ""}

![Flowchart](./{flow_img})

{analysis}

{steps}

{q_and_a}
"""
    with open(output_dir / f"{file_path.stem}.md", "w", encoding="utf-8") as f:
        f.write(markdown)


def main():
    parser = argparse.ArgumentParser(description="Generate Markdown documentation for Python files.")
    parser.add_argument("files", nargs="+", help="File(s) or folder(s) to document")
    parser.add_argument("-o", "--output", default="docs", help="Output directory (default: docs/)")
    parser.add_argument("--max-depth", type=int, default=4, help="Max folder recursion depth (default: 4)")
    args = parser.parse_args()

    files = find_py_files(args.files, args.max_depth)
    output_dir = Path(args.output).resolve()

    if not files:
        print("❌ No valid Python files found.")
        return

    for file_path in sorted(files):
        print(f"📄 Documenting: {file_path}")
        try:
            generate_markdown(file_path, output_dir)
        except Exception as e:
            print(f"⚠️  Skipped {file_path.name} due to error: {e}")

    print(f"\n✅ Documentation generated in: {output_dir}")


if __name__ == "__main__":
    main()
