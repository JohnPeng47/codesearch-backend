import argparse
import json
from pathlib import Path
from typing import List, Optional

def generate_tree(
    directory: Path,
    exclusions: List[str] = None,
    indent: str = "  ",
    prefix: str = "",
) -> str:
    """Generate a directory tree string."""
    if exclusions is None:
        exclusions = []
    
    output = []
    try:
        # Sort directories first, then files
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        return f"{prefix}[Permission Denied]\n"

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        node_prefix = "└── " if is_last else "├── "
        
        # Check if item should be excluded
        if any(item.match(pattern) for pattern in exclusions):
            continue

        rel_path = str(item.relative_to(directory.parent))
        if item.is_dir():
            output.append(f"{prefix}{node_prefix}{item.name}/")
            next_prefix = prefix + ("    " if is_last else "│   ")
            output.append(generate_tree(item, exclusions, indent, next_prefix))
        else:
            try:
                with open(item, "r", encoding="utf-8") as f:
                    content = f.read()
                output.append(f"{prefix}{node_prefix}{item.name}")
            except (UnicodeDecodeError, PermissionError):
                output.append(f"{prefix}{node_prefix}{item.name} [Binary or inaccessible]")

    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(
        description="Generate a directory tree with optional file content concatenation"
    )
    parser.add_argument("directory", help="The directory to process")
    parser.add_argument("-e", "--exclude", action="append", default=[],
                        help="Exclusion patterns (can be used multiple times)")
    parser.add_argument("--output", choices=["text", "json"], default="text",
                        help="Output format (text or json)")

    args = parser.parse_args()

    # Default exclusions including examples and tests
    default_exclusions = [
        "examples/*",
        "tests/*",
        ".venv/*",
        "__pycache__/*",
        "*.pyc",
        ".git/*",
        ".idea/*",
        ".vscode/*",
        "node_modules/*",
        "build/*",
        "dist/*",
        "*.egg-info/*",
        ".pytest_cache/*",
        ".coverage",
        "htmlcov/*",
    ]

    # Combine user-provided exclusions with default exclusions
    exclusions = default_exclusions + args.exclude
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return

    tree = generate_tree(directory, exclusions=exclusions)
    
    if args.output == "json":
        result = {
            "directory": str(directory),
            "tree": tree.split("\n"),
            "exclusions": exclusions
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\nDirectory Tree for: {directory}\n")
        print(tree)
        print("\nExclusion patterns:", ", ".join(exclusions))

if __name__ == "__main__":
    main()
