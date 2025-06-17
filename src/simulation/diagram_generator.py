"""
Diagram Generator Module
========================
Handles generation of Mermaid diagrams and flowcharts.
Follows SRP: Single responsibility for visual diagram creation.
"""

import ast
from typing import List
from urllib.parse import quote


def extract_class_info(node: ast.ClassDef) -> List[str]:
    """Extract class information for Mermaid diagram."""
    class_lines = [f"  class {node.name}"]
    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            class_lines.append(f"  {node.name} : {item.name}()")
    return class_lines


def generate_mermaid_class_diagram(tree: ast.Module) -> str:
    """Generate Mermaid class diagram from AST."""
    lines = ["```mermaid", "classDiagram"]
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            lines.extend(extract_class_info(node))
    lines.append("```")
    return "\n".join(lines)


def create_function_flowchart(tree: ast.Module) -> List[str]:
    """Create flowchart lines for functions from AST."""
    lines = ["```mermaid", "flowchart TD"]
    prev = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if prev:
                lines.append(f"  {prev} --> {node.name}")
            prev = node.name
    lines.append("```")
    return lines


def generate_mermaid_flowchart(tree: ast.Module) -> str:
    """Generate Mermaid flowchart from AST."""
    return "\n".join(create_function_flowchart(tree))


def generate_pythontutor_link(source: str) -> str:
    """Generate Python Tutor visualization link for source code."""
    base_url = "https://pythontutor.com/visualize.html#code="
    encoded = quote(source)
    return f"[▶ Visualize in Python Tutor]({base_url}{encoded}&cumulative=false&heapPrimitives=false&mode=display&py=3)"
