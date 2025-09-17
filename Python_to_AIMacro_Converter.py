#!/usr/bin/env python3
"""
Python to AIMacro Converter
Automatically converts Python files to AIMacro syntax by adding semicolons and end markers
Version: 1.0

Usage:
    python python_to_aimacro.py input.py output.aimacro
    python python_to_aimacro.py --dir ./python_files ./aimacro_files
"""

import ast
import sys
import os
import argparse
import textwrap
from pathlib import Path
from typing import List, Tuple, Optional

class PythonToAIMacroConverter:
    """Converts Python source code to AIMacro syntax"""
    
    def __init__(self, preserve_comments=True, add_semicolons=True):
        self.preserve_comments = preserve_comments
        self.add_semicolons = add_semicolons
        self.indent_stack = []
        self.current_indent = 0
        
    def convert_file(self, input_file: str, output_file: str = None) -> str:
        """Convert a Python file to AIMacro"""
        with open(input_file, 'r') as f:
            source = f.read()
        
        converted = self.convert_source(source)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(converted)
            print(f"✅ Converted {input_file} -> {output_file}")
        
        return converted
    
    def convert_source(self, source: str) -> str:
        """Convert Python source code to AIMacro"""
        lines = source.split('\n')
        result = []
        
        # Track context for proper end; placement
        block_stack = []  # Stack of (type, indent_level) tuples
        prev_indent = 0
        in_class = False
        in_function = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            
            # Skip empty lines and preserve them
            if not stripped:
                result.append(line)
                i += 1
                continue
            
            # Preserve comments
            if stripped.startswith('#'):
                result.append(line)
                i += 1
                continue
            
            # Handle dedentation - add end; statements
            while block_stack and indent < block_stack[-1][1]:
                block_type, block_indent = block_stack.pop()
                # Add proper indentation for the end;
                result.append(' ' * block_indent + 'end;')
                if block_type == 'class':
                    in_class = False
                elif block_type == 'def':
                    in_function = False
            
            # Check for block-starting keywords
            block_type = self._get_block_type(stripped)
            
            if block_type:
                # This line starts a block
                modified_line = self._process_block_start(line, stripped, block_type)
                result.append(modified_line)
                
                # Add to block stack
                block_stack.append((block_type, indent))
                
                if block_type == 'class':
                    in_class = True
                elif block_type == 'def':
                    in_function = True
                    
            else:
                # Regular statement - maybe add semicolon
                modified_line = self._process_statement(line, stripped)
                result.append(modified_line)
            
            i += 1
        
        # Close any remaining blocks
        while block_stack:
            block_type, block_indent = block_stack.pop()
            result.append(' ' * block_indent + 'end;')
        
        return '\n'.join(result)
    
    def _get_block_type(self, stripped: str) -> Optional[str]:
        """Determine if a line starts a block"""
        block_keywords = {
            'def ': 'def',
            'class ': 'class',
            'if ': 'if',
            'elif ': 'elif',
            'else:': 'else',
            'else ': 'else',
            'for ': 'for',
            'while ': 'while',
            'try:': 'try',
            'try ': 'try',
            'except': 'except',
            'finally:': 'finally',
            'finally ': 'finally',
            'with ': 'with',
        }
        
        for keyword, block_type in block_keywords.items():
            if stripped.startswith(keyword):
                return block_type
        
        # Check for lambda (special case)
        if 'lambda' in stripped and ':' in stripped:
            return None  # Lambda doesn't need end;
            
        return None
    
    def _process_block_start(self, line: str, stripped: str, block_type: str) -> str:
        """Process a line that starts a block"""
        # Most block starters already have : at the end in Python
        # Just return as-is, the : is already there
        return line
    
    def _process_statement(self, line: str, stripped: str) -> str:
        """Process a regular statement"""
        if not self.add_semicolons:
            return line
        
        # Don't add semicolons to certain statements
        skip_semicolon = [
            'pass',
            'break', 
            'continue',
            'return',
            'yield',
            'raise',
            'import ',
            'from ',
            'global ',
            'nonlocal ',
        ]
        
        # Check if we should skip semicolon
        for keyword in skip_semicolon:
            if stripped.startswith(keyword):
                # These already work well, but we'll add ; for consistency
                if not stripped.endswith(';'):
                    return line + ';'
                return line
        
        # Don't add semicolon if line ends with : or ; already
        if stripped.endswith(':') or stripped.endswith(';'):
            return line
        
        # Don't add semicolon to decorators
        if stripped.startswith('@'):
            return line
        
        # Don't add semicolon to multiline continuations
        if stripped.endswith('\\'):
            return line
        
        # Add semicolon to regular statements
        if stripped and not stripped.startswith('#'):
            return line + ';'
        
        return line

class AdvancedPythonToAIMacro:
    """Advanced converter using AST parsing for better accuracy"""
    
    def __init__(self):
        self.source_lines = []
        self.result_lines = []
        self.block_ends = {}  # Maps line numbers to required end; statements
        
    def convert_source(self, source: str) -> str:
        """Convert using Python's AST for accurate parsing"""
        self.source_lines = source.split('\n')
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            print(f"Warning: Could not parse Python AST, using simple conversion: {e}")
            # Fall back to simple converter
            simple_converter = PythonToAIMacroConverter()
            return simple_converter.convert_source(source)
        
        # Analyze AST to find where blocks end
        self._analyze_ast(tree)
        
        # Build result with end; markers
        return self._build_result()
    
    def _analyze_ast(self, tree):
        """Analyze AST to find block boundaries"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.If, ast.For, ast.While, ast.With, ast.Try)):
                # These nodes need end; after their body
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    end_line = node.end_lineno
                    if end_line not in self.block_ends:
                        self.block_ends[end_line] = []
                    
                    # Determine indentation level
                    if node.lineno <= len(self.source_lines):
                        line = self.source_lines[node.lineno - 1]
                        indent = len(line) - len(line.lstrip())
                        self.block_ends[end_line].append(indent)
    
    def _build_result(self) -> str:
        """Build the result with end; markers added"""
        result = []
        
        for i, line in enumerate(self.source_lines, 1):
            stripped = line.lstrip()
            
            # Add the original line (possibly with semicolon)
            if stripped and not stripped.startswith('#') and not stripped.endswith(':') and not stripped.endswith(';'):
                # Add semicolon to regular statements
                if not any(stripped.startswith(kw) for kw in ['def ', 'class ', 'if ', 'elif ', 'else', 'for ', 'while ', 'try', 'except', 'finally', 'with ']):
                    line = line + ';'
            
            result.append(line)
            
            # Add end; statements if this line ends a block
            if i in self.block_ends:
                for indent in self.block_ends[i]:
                    result.append(' ' * indent + 'end;')
        
        return '\n'.join(result)

def convert_directory(input_dir: str, output_dir: str, recursive: bool = False):
    """Convert all Python files in a directory"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all Python files
    if recursive:
        python_files = input_path.rglob('*.py')
    else:
        python_files = input_path.glob('*.py')
    
    converter = PythonToAIMacroConverter()
    converted_count = 0
    
    for py_file in python_files:
        # Calculate relative path for output
        rel_path = py_file.relative_to(input_path)
        
        # Change extension to .aimacro
        output_file = output_path / rel_path.with_suffix('.aimacro')
        
        # Create output subdirectories if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            converter.convert_file(str(py_file), str(output_file))
            converted_count += 1
        except Exception as e:
            print(f"❌ Error converting {py_file}: {e}")
    
    print(f"\n✨ Converted {converted_count} files successfully!")

def main():
    parser = argparse.ArgumentParser(
        description='Convert Python files to AIMacro syntax',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Examples:
            # Convert a single file
            python python_to_aimacro.py script.py script.aimacro
            
            # Convert all Python files in a directory
            python python_to_aimacro.py --dir ./python_code ./aimacro_code
            
            # Convert recursively
            python python_to_aimacro.py --dir ./src ./converted --recursive
            
            # Use advanced AST-based conversion
            python python_to_aimacro.py --advanced input.py output.aimacro
        ''')
    )
    
    parser.add_argument('input', nargs='?', help='Input Python file')
    parser.add_argument('output', nargs='?', help='Output AIMacro file')
    parser.add_argument('--dir', nargs=2, metavar=('INPUT_DIR', 'OUTPUT_DIR'),
                       help='Convert all Python files in directory')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='Recursively convert subdirectories')
    parser.add_argument('--no-semicolons', action='store_true',
                       help='Don\'t add semicolons to statements')
    parser.add_argument('--advanced', action='store_true',
                       help='Use advanced AST-based conversion')
    parser.add_argument('--test', action='store_true',
                       help='Run test conversions to verify functionality')
    
    args = parser.parse_args()
    
    if args.test:
        run_tests()
        return
    
    if args.dir:
        input_dir, output_dir = args.dir
        convert_directory(input_dir, output_dir, args.recursive)
    elif args.input:
        # Single file conversion
        output = args.output
        if not output:
            # Auto-generate output filename
            input_path = Path(args.input)
            output = str(input_path.with_suffix('.aimacro'))
        
        if args.advanced:
            converter = AdvancedPythonToAIMacro()
            with open(args.input, 'r') as f:
                source = f.read()
            result = converter.convert_source(source)
            with open(output, 'w') as f:
                f.write(result)
            print(f"✅ Advanced conversion: {args.input} -> {output}")
        else:
            converter = PythonToAIMacroConverter(add_semicolons=not args.no_semicolons)
            converter.convert_file(args.input, output)
    else:
        parser.print_help()

def run_tests():
    """Run test conversions to verify functionality"""
    print("Running conversion tests...\n")
    print("=" * 60)
    
    test_cases = [
        # Test 1: Simple function
        ("""def add(x, y):
    return x + y""",
         """def add(x, y):
    return x + y;
end;"""),
        
        # Test 2: Nested blocks
        ("""def process(data):
    if len(data) > 0:
        for item in data:
            print(item)
    else:
        print("Empty")""",
         """def process(data):
    if len(data) > 0:
        for item in data:
            print(item);
        end;
    else:
        print("Empty");
    end;
end;"""),
        
        # Test 3: Class definition
        ("""class MyClass:
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        return self.value""",
         """class MyClass:
    def __init__(self, value):
        self.value = value;
    end;
    
    def get_value(self):
        return self.value;
    end;
end;"""),
        
        # Test 4: While loop with break
        ("""def find(items, target):
    i = 0
    while i < len(items):
        if items[i] == target:
            return i
        i += 1
    return -1""",
         """def find(items, target):
    i = 0;
    while i < len(items):
        if items[i] == target:
            return i;
        end;
        i += 1;
    end;
    return -1;
end;"""),
    ]
    
    converter = PythonToAIMacroConverter()
    passed = 0
    failed = 0
    
    for i, (input_code, expected) in enumerate(test_cases, 1):
        print(f"Test {i}: ", end="")
        result = converter.convert_source(input_code)
        
        # Normalize whitespace for comparison
        result_lines = [line.strip() for line in result.strip().split('\n') if line.strip()]
        expected_lines = [line.strip() for line in expected.strip().split('\n') if line.strip()]
        
        if result_lines == expected_lines:
            print("✅ PASSED")
            passed += 1
        else:
            print("❌ FAILED")
            print("  Expected:")
            for line in expected_lines:
                print(f"    {line}")
            print("  Got:")
            for line in result_lines:
                print(f"    {line}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✨ All tests passed!")
    else:
        print("⚠️  Some tests failed. Please review.")

if __name__ == "__main__":
    main()
