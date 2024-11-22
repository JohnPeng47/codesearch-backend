#!/usr/bin/env python3

import os
import ast
import argparse
from typing import List, Set, Tuple, Dict, Optional
from dataclasses import dataclass
import logging
import fnmatch
import yaml
from pathlib import Path

CONFIG_DIR = "llm"

# Default exclusions
DEFAULT_EXCLUSIONS = [
    "__pycache__",
    "versions/*",
    "alembic/*",
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
    "tests/**", 
    ".pytest_cache/*",
    ".coverage",
    "htmlcov/*"
]

@dataclass
class LLMFunctionCall:
    file_path: str
    function_name: str
    line_number: int
    line_content: str

class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.var_names = set()
        
    def visit_AnnAssign(self, node):
        # Add check for function parameters with LLMModel type annotation
        if (isinstance(node.annotation, ast.Name) and 
            node.annotation.id == 'LLMModel' and 
            isinstance(node.target, ast.Name)):
            self.var_names.add(node.target.id)
        self.generic_visit(node)
        
    def visit_arg(self, node):
        # Add handling for function parameters
        if (hasattr(node, 'annotation') and 
            isinstance(node.annotation, ast.Name) and 
            node.annotation.id == 'LLMModel'):
            self.var_names.add(node.arg)
        self.generic_visit(node)

class InvokeCallVisitor(ast.NodeVisitor):
    def __init__(self, llm_var_names: Set[str]):
        self.calls = []
        self.current_function = None
        self.llm_var_names = llm_var_names
        
    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = None
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'invoke':
            # Check if the invoke is called on one of our LLM variables
            if isinstance(node.func.value, ast.Name) and node.func.value.id in self.llm_var_names:
                if self.current_function:
                    self.calls.append(LLMFunctionCall(
                        file_path="",
                        function_name=self.current_function,
                        line_number=node.lineno,
                        line_content=ast.unparse(node)
                    ))
        self.generic_visit(node)

def check_llm_import(content: str) -> Tuple[bool, Set[str]]:
    """Check if LLMModel is imported and get possible variable names using AST."""
    try:
        tree = ast.parse(content)
        visitor = ImportVisitor()
        visitor.visit(tree)
        return bool(visitor.var_names), visitor.var_names
    except SyntaxError:
        return False, set()

def find_invoke_calls(content: str, llm_var_names: Set[str], line_offset: int = 0) -> List[LLMFunctionCall]:
    """Find functions that contain .invoke() calls using AST."""
    try:
        tree = ast.parse(content)
        visitor = InvokeCallVisitor(llm_var_names)
        visitor.visit(tree)
        
        # Adjust line numbers with offset
        for call in visitor.calls:
            call.line_number += line_offset
        return visitor.calls
    except SyntaxError:
        return []

def should_skip_path(path: str, exclusions: List[str]) -> bool:
    """Check if a path should be skipped based on exclusion patterns."""
    for pattern in exclusions:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
    return False

def scan_directory(directory: str, llm_path: str = "llm", exclusions: List[str] = DEFAULT_EXCLUSIONS) -> List[LLMFunctionCall]:
    """Scan directory for Python files containing LLMModel invoke calls."""
    results = []
    directory = os.path.normpath(directory)
    
    roots_to_scan = []
    for root, dirs, _ in os.walk(directory, topdown=True):
        rel_path = os.path.relpath(root, directory)
        rel_path = rel_path.replace(os.sep, '/')
        
        if should_skip_path(rel_path, exclusions):
            dirs.clear()
            continue
        roots_to_scan.append(root)
    
    for root in roots_to_scan:
        for file in os.listdir(root):
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            rel_file_path = os.path.relpath(file_path, directory)
            rel_file_path = rel_file_path.replace(os.sep, '/')

            if should_skip_path(rel_file_path, exclusions):
                continue
                
            try:
                logging.info(f"Checking: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                has_import, var_names = check_llm_import(content)
                logging.info(f"Imports: {var_names}")
                if not has_import:
                    continue
                    
                if llm_path != "llm":
                    logging.warning(f"File uses 'llm' import but specified path was {llm_path}")
                
                calls = find_invoke_calls(content, var_names)
                logging.info(f"Calls: {calls}")
                if calls:
                    for call in calls:
                        call.file_path = file_path
                    results.extend(calls)
                else:
                    logging.info("No invoke calls found in file")
                    
            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
    
    return results

def load_yaml_config(config_path: str) -> Dict[str, list]:
    """Load existing function configurations from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

def update_yaml_config(config_path: str, results: List[LLMFunctionCall], existing_config: Dict[str, list]):
    """Update YAML config with newly discovered functions."""
    # Create new entries for discovered functions
    for result in results:
        if result.function_name not in existing_config:
            existing_config[result.function_name] = [
                {'cache': False},
                {'filepath': str(result.file_path)}
            ]
        else:
            # Update filepath if it doesn't exist in the current config
            has_filepath = any('filepath' in item for item in existing_config[result.function_name])
            if not has_filepath:
                existing_config[result.function_name].append({'filepath': str(result.file_path)})
    
    # Write updated config back to file
    with open(config_path, 'w') as f:
        yaml.dump(existing_config, f, sort_keys=True, default_flow_style=False)

def reset_cache_config(config_path: str) -> List[str]:
    """Reset all cache settings to false and return list of modified functions."""
    modified_functions = []
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        # Find and reset all cache: true settings
        for func_name, settings in config.items():
            for item in settings:
                if isinstance(item, dict) and 'cache' in item and item['cache']:
                    item['cache'] = False
                    modified_functions.append(func_name)
        
        # Write updated config back to file
        with open(config_path, 'w') as f:
            yaml.dump(config, f, sort_keys=True, default_flow_style=False)
            
        return modified_functions
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        return []

def list_cached_functions(config_dir: str) -> None:
    """List all YAML files and their cached functions."""
    if not os.path.exists(config_dir):
        print(f"Config directory {config_dir} not found")
        return

    yaml_files = [f for f in os.listdir(config_dir) if f.endswith('.yaml')]
    
    if not yaml_files:
        print(f"No YAML files found in {config_dir}")
        return

    for yaml_file in yaml_files:
        file_path = os.path.join(config_dir, yaml_file)
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Find functions with cache: true
            cached_functions = []
            for func_name, settings in config.items():
                for item in settings:
                    if isinstance(item, dict) and 'cache' in item and item['cache']:
                        cached_functions.append(func_name)
                        break
            
            print(f"\nFile: {yaml_file}")
            if cached_functions:
                print("Cached functions:")
                for func_name in sorted(cached_functions):
                    print(f"  - {func_name}")
            else:
                print("No cached functions found")
                
        except Exception as e:
            print(f"Error reading {yaml_file}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Scan for LLMModel invoke calls in Python files.')
    parser.add_argument('directory', nargs='?', help='Directory to scan')
    parser.add_argument('--llm-path', default='llm', help='Expected import path for LLMModel')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--no-exclusions', action='store_true', help='Disable default exclusions')
    parser.add_argument('--config', default=f'{CONFIG_DIR}/cache.yaml', help='Path to YAML config file')
    parser.add_argument('--reset', action='store_true', help='Reset all cache settings to false')
    parser.add_argument('--list', action='store_true', help='List all YAML files and their cached functions')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s'
    )
    
    if args.list:
        list_cached_functions(f"{CONFIG_DIR}/cache")
        return
        
    if args.reset:
        modified = reset_cache_config(args.config)
        if modified:
            print("Reset cache for the following functions:")
            for func_name in modified:
                print(f"  - {func_name}")
        else:
            print("No cached functions found to reset")
        return

    if not args.directory:
        parser.error("directory argument is required unless using --reset or --list")

    existing_config = load_yaml_config(args.config)
    exclusions = [] if args.no_exclusions else DEFAULT_EXCLUSIONS
    results = scan_directory(args.directory, args.llm_path, exclusions)
    
    if not results:
        return
    
    # Print only new functions
    new_functions = [call for call in results if call.function_name not in existing_config]
    print("New LLM invoke functions found: ", len(new_functions))
    
    if new_functions:
        for call in new_functions:
            relative_path = os.path.relpath(call.file_path, os.getcwd())
            print(f"Function: {call.function_name}, Path: {relative_path}")
    
    update_yaml_config(args.config, results, existing_config)

if __name__ == '__main__':
    main()