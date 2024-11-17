#!/usr/bin/env python3

import argparse
import re
from typing import List, Pattern

def test_patterns(filepath: str, patterns: List[Pattern]) -> None:
    """Test regex patterns against content of a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find function definitions and invoke calls
        function_pattern = re.compile(r'def\s+(\w+)\s*\([^)]*\):')
        invoke_pattern = re.compile(r'\.invoke\s*\(')
        
        current_function = None
        for i, line in enumerate(content.split('\n'), start=1):
            # Check for function definition
            func_match = function_pattern.search(line)
            if func_match:
                current_function = func_match.group(1)
                print(f"\nFound function definition: {current_function} at line {i}")
            
            # Check for invoke call
            if current_function and invoke_pattern.search(line):
                print(f"Found invoke call in function {current_function} at line {i}")
                print(f"Line content: {line.strip()}")
            
            # Check for end of function (less indentation)
            if current_function and line.strip() and not line.startswith(' '):
                current_function = None

    except FileNotFoundError:
        print(f"Error: File {filepath} not found")
    except Exception as e:
        print(f"Error processing file: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Test regex patterns on a file')
    parser.add_argument('filepath', help='Path to the file to test patterns against')
    args = parser.parse_args()

    # Only use the invoke pattern from file_context_0
    patterns = [
        re.compile(r'\.invoke\s*\(')
    ]

    test_patterns(args.filepath, patterns)

if __name__ == '__main__':
    main()
