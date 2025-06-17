"""
Functional Metrics Module
=========================
Handles code analysis and functional quality metrics.
Follows SRP: Single responsibility for code analysis.
"""

import ast
from pathlib import Path
from typing import List

try:
    import asttokens
except ImportError:
    asttokens = None


def analyze_function(node: ast.FunctionDef) -> List[str]:
    """
    Analyze a function node and extract documentation.
    
    Args:
        node: AST FunctionDef node to analyze
        
    Returns:
        List[str]: Function analysis as markdown lines
    """
    explanation = [f"### Function `{node.name}`"]
    args = [arg.arg for arg in node.args.args]
    explanation.append(f"**Arguments:** {args}")
    explanation.append(f"**Docstring:** {ast.get_docstring(node)}")
    explanation.append("**Explanation:** This function likely performs...")
    return explanation


def analyze_class(node: ast.ClassDef) -> List[str]:
    """
    Analyze a class node and extract documentation.
    
    Args:
        node: AST ClassDef node to analyze
        
    Returns:
        List[str]: Class analysis as markdown lines
    """
    explanation = [f"## Class `{node.name}`"]
    explanation.append(f"**Docstring:** {ast.get_docstring(node)}")
    explanation.append("**Explanation:** This class is responsible for...")
    return explanation


def analyze_code(source: str) -> str:
    """
    Analyze source code and generate functional explanations.
    
    Args:
        source: Source code string to analyze
        
    Returns:
        str: Markdown-formatted code analysis
    """
    if asttokens:
        atok = asttokens.ASTTokens(source, parse=True)
        tree = atok.tree
    else:
        tree = ast.parse(source)
    
    explanation = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            explanation.extend(analyze_function(node))
        elif isinstance(node, ast.ClassDef):
            explanation.extend(analyze_class(node))
    return "\n".join(explanation)


def get_ast_tree(source: str) -> ast.Module:
    """
    Parse source code and return AST tree.
    
    Args:
        source: Source code string to parse
        
    Returns:
        ast.Module: Parsed AST tree
    """
    if asttokens:
        atok = asttokens.ASTTokens(source, parse=True)
        return atok.tree
    else:
        return ast.parse(source)


def generate_interview_qa(file_path: Path) -> str:
    """
    Generate interview Q&A section for a file.
    
    Args:
        file_path: Path to the file being documented
        
    Returns:
        str: Markdown-formatted interview Q&A section
    """
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


def generate_step_by_step() -> str:
    """
    Generate step-by-step execution guide.
    
    Returns:
        str: Markdown-formatted step-by-step guide
    """
    return """
## Step-by-Step Execution

1. Load and parse the input file.
2. Construct AST and tokenize.
3. Identify main structures (classes/functions).
4. Generate Mermaid diagrams.
5. Write detailed markdown with explanation.
"""
