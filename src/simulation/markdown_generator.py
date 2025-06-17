"""
Markdown Generator Module
=========================
Handles markdown content generation and formatting.
Follows SRP: Single responsibility for markdown document creation.
"""

from pathlib import Path
from typing import List

from .diagram_generator import (
    generate_mermaid_class_diagram,
    generate_mermaid_flowchart,
    generate_pythontutor_link
)
from .functional_metrics import (
    analyze_code,
    generate_interview_qa,
    generate_step_by_step,
    get_ast_tree
)
from .non_functional_metrics import (
    benchmark_serialization,
    generate_metrics_table,
    get_default_benchmark_data
)


def generate_table_of_contents(include_toc: bool) -> str:
    """
    Generate table of contents section if requested.
    
    Args:
        include_toc: Whether to include TOC in output
        
    Returns:
        str: Table of contents markdown or empty string
    """
    if not include_toc:
        return ""
    
    return """## Table of Contents
- [Class Diagram](#class-diagram)
- [Flowchart](#flowchart)
- [Python Tutor](#live-execution)
- [Analysis](#analysis)
- [Execution](#step-by-step-execution)
- [Performance](#performance-metrics-summary)
- [Interview Q&A](#interview-qa)
"""


def generate_markdown_content(file_path: Path, source: str, include_toc: bool) -> str:
    """
    Generate complete markdown content for a Python file.
    
    Args:
        file_path: Path to the source file
        source: Source code content
        include_toc: Whether to include table of contents
        
    Returns:
        str: Complete markdown document
    """
    # Get AST tree for analysis
    tree = get_ast_tree(source)
    
    # Generate all sections
    toc_section = generate_table_of_contents(include_toc)
    class_diagram = generate_mermaid_class_diagram(tree)
    flowchart = generate_mermaid_flowchart(tree)
    analysis = analyze_code(source)
    q_and_a = generate_interview_qa(file_path)
    steps = generate_step_by_step()
    pythontutor = generate_pythontutor_link(source)
    
    # Generate performance metrics
    benchmark_data = get_default_benchmark_data()
    metrics = benchmark_serialization(benchmark_data)
    metrics_table = generate_metrics_table(metrics)

    # Combine all sections into final markdown
    markdown = f"""# Documentation for `{file_path.name}`

{toc_section}

## Class Diagram
{class_diagram}

## Flowchart
{flowchart}

## Live Execution
{pythontutor}

## Analysis
{analysis}

{steps}

{metrics_table}

{q_and_a}
"""
    return markdown


def generate_markdown(file_path: Path, output_dir: Path, toc: bool) -> str:
    """
    Generate markdown documentation for a Python file.
    
    Args:
        file_path: Path to the Python file to document
        output_dir: Directory to save generated documentation
        toc: Whether to include table of contents
        
    Returns:
        str: Name of the generated markdown file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    source = file_path.read_text(encoding="utf-8")
    
    markdown_content = generate_markdown_content(file_path, source, toc)
    
    # Prepend subpackage name to avoid overwriting
    subpackage = file_path.parent.name
    out_file = output_dir / f"{subpackage}.{file_path.stem}.md"
    out_file.write_text(markdown_content, encoding="utf-8")
    return out_file.name


def generate_index(md_files: List[str], output_dir: Path) -> None:
    """
    Generate index file with links to all documentation.
    
    Args:
        md_files: List of markdown file names
        output_dir: Directory to save the index file
    """
    lines = ["# Documentation Index\n"]
    # Remove duplicates by converting to set, then back to sorted list
    unique_files = sorted(set(md_files))
    for name in unique_files:
        rel = Path(name).name
        lines.append(f"- [{rel}](./{rel})")
    (output_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")
