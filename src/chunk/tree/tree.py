import argparse
import json
from pathlib import Path
from typing import List, Optional

from src.common import EXTTOFILE, FILETOEXT

def load_config_exclusions() -> List[str]:
    """Load exclusion patterns from .tree.config file if it exists."""
    config_file = Path('.tree.config')
    config_exists = config_file.exists()
    exclusions = []
    
    if config_exists:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                exclusions = config.get('exclude', [])
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not parse {config_file}")
    
    return exclusions

def generate_tree(
    directory: Path,
    exclusions: List[str] = None,
    indent: str = "  ",
    prefix: str = "",
) -> str:
    """Generate a directory tree string."""
    # Initialize control flags and state
    has_permission = True
    exclusions = exclusions or []
    output = []
    items = []

    # Get directory contents
    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        has_permission = False

    # Handle permission denied case
    if not has_permission:
        return f"{prefix}[Permission Denied]\n"

    # Process each item
    for i, item in enumerate(items):
        # Control flags for current item
        is_last = i == len(items) - 1
        should_exclude = any(item.match(pattern) for pattern in exclusions)
        is_directory = item.is_dir()
        
        # Skip excluded items
        if should_exclude:
            continue

        # Prepare formatting
        node_prefix = "└── " if is_last else "├── "
        next_prefix = prefix + ("    " if is_last else "│   ")

        # Handle directories
        if is_directory:
            output.append(f"{prefix}{node_prefix}{item.name}/")
            subtree = generate_tree(item, exclusions, indent, next_prefix)
            output.append(subtree)
            continue

        # Handle files
        try:
            output.append(f"{prefix}{node_prefix}{item.name}")
        except (UnicodeDecodeError, PermissionError):
            output.append(f"{prefix}{node_prefix}{item.name} [Binary or inaccessible]")

    return "\n".join(output)

def main():
    # Default exclusions
    DEFAULT_EXCLUSIONS = [
        "cowboy_lib/*",
        "rtfs_rewrite/*", 
        ".venv/*",
        "notebooks/*",
        "__pycache__/*",
        "*.pyc",
        ".git/*", 
        ".idea/*",
        ".vscode/*",
        "node_modules/*",
        "build/*",
        "dist/*",
        "*.egg-info/*",
        "cache/*",
        "*.db",
        "examples/*", 
        "tests/*",
        ".pytest_cache/*",
        ".coverage",
        "htmlcov/*"
    ]

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Generate a directory tree with optional file content concatenation"
    )
    parser.add_argument("directory", help="The directory to process")
    parser.add_argument("-e", "--exclude", action="append", default=[],
                        help="Exclusion patterns (can be used multiple times)")
    parser.add_argument("--output", choices=["text", "json"], default="text",
                        help="Output format (text or json)")
    args = parser.parse_args()
    
    # Initialize control flags and state
    directory = Path(args.directory)
    directory_exists = directory.exists()
    output_format = args.output
    
    # Validate directory
    if not directory_exists:
        print(f"Error: Directory '{directory}' does not exist")
        return

    # Prepare exclusions
    config_exclusions = load_config_exclusions()
    exclusions = DEFAULT_EXCLUSIONS + config_exclusions + args.exclude

    # Generate tree
    tree = generate_tree(directory, exclusions=exclusions)

    # Output results
    if output_format == "json":
        result = {
            "directory": str(directory),
            "tree": tree.split("\n"),
            "exclusions": exclusions
        }
        print(json.dumps(result, indent=2))
    else:
        with open("tree.txt", "w", encoding="utf-8") as f:
            f.write(tree)

if __name__ == "__main__":
    main()
