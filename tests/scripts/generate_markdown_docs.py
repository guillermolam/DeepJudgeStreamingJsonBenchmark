import os
import sys
import importlib.util
import inspect
from typing import Any, Dict, List, Optional, Tuple

# Add the src directory to the Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, src_path)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

def get_parser_metadata(parser_module):
    if hasattr(parser_module, 'get_metadata'):
        return parser_module.get_metadata()
    return {}

def generate_class_diagram(module):
    classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]
    diagram = "classDiagram\n"
    for cls in classes:
        diagram += f"  class {cls}\n"
        methods = [name for name, obj in inspect.getmembers(getattr(module, cls), inspect.isfunction)]
        for method in methods:
            diagram += f"  {cls} : {method}()\n"
    return diagram

def generate_flowchart(module):
    functions = [name for name, obj in inspect.getmembers(module, inspect.isfunction)]
    flowchart = "flowchart TD\n"
    for i in range(len(functions) - 1):
        flowchart += f"  {functions[i]} --> {functions[i+1]}\n"
    return flowchart

def generate_markdown_for_file(filepath: str, output_dir: str):
    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    metadata = get_parser_metadata(module)
    class_diagram = generate_class_diagram(module)
    flowchart = generate_flowchart(module)

    with open(os.path.join(output_dir, f"{module_name}.md"), "w") as f:
        f.write(f"# Documentation for `{os.path.basename(filepath)}`\n\n")
        if metadata:
            f.write("## Metadata\n")
            for key, value in metadata.items():
                f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
            f.write("\n")
        
        f.write("## Class Diagram\n")
        f.write(f"```mermaid\n{class_diagram}\n```\n\n")
        
        f.write("## Flowchart\n")
        f.write(f"```mermaid\n{flowchart}\n```\n\n")

def main():
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create subdirectories for each category
    categories = ['anyio', 'raw', 'solid']
    for category in categories:
        category_dir = os.path.join(output_dir, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith("_parser.py"):
                filepath = os.path.join(root, file)
                # Determine the category from the path
                relative_path = os.path.relpath(root, input_dir)
                if relative_path != '.':
                    category_output_dir = os.path.join(output_dir, relative_path)
                    if not os.path.exists(category_output_dir):
                        os.makedirs(category_output_dir)
                else:
                    category_output_dir = output_dir
                generate_markdown_for_file(filepath, category_output_dir)

if __name__ == "__main__":
    main()
