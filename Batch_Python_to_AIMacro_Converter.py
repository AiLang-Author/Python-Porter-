#!/usr/bin/env python3
"""
Batch Python to AIMacro Converter
Handles importing Python modules and converting them to AIMacro
Includes dependency resolution and library mapping
"""

import os
import sys
import ast
import json
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple
import importlib.util
import argparse

class PythonProjectConverter:
    """Convert entire Python projects to AIMacro"""
    
    def __init__(self, project_root: str, output_dir: str):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.converted_modules = set()
        self.import_map = {}
        self.failed_conversions = []
        
        # Standard library modules that should be mapped to AIMacro equivalents
        self.stdlib_mappings = {
            'math': 'Library.AIMacro.Math',
            'random': 'Library.AIMacro.Random',
            'os': 'Library.AIMacro.System',
            'sys': 'Library.AIMacro.System',
            'json': 'Library.AIMacro.JSON',
            're': 'Library.AIMacro.Regex',
            'datetime': 'Library.AIMacro.DateTime',
            'collections': 'Library.AIMacro.Collections',
            'itertools': 'Library.AIMacro.Itertools',
            'functools': 'Library.AIMacro.Functional',
        }
        
    def convert_project(self):
        """Convert entire Python project to AIMacro"""
        print(f"🚀 Starting project conversion: {self.project_root}")
        print(f"📁 Output directory: {self.output_dir}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all Python files
        python_files = list(self.project_root.rglob('*.py'))
        print(f"📊 Found {len(python_files)} Python files")
        
        # Analyze dependencies
        print("\n🔍 Analyzing dependencies...")
        dependency_graph = self._analyze_dependencies(python_files)
        
        # Sort by dependencies (files with no deps first)
        sorted_files = self._topological_sort(dependency_graph)
        
        # Convert files in order
        print("\n🔄 Converting files...")
        for py_file in sorted_files:
            self._convert_file(py_file)
        
        # Create import mapping file
        self._create_import_mapping()
        
        # Generate project manifest
        self._create_project_manifest()
        
        # Print summary
        self._print_summary()
    
    def _analyze_dependencies(self, python_files: List[Path]) -> Dict[Path, Set[Path]]:
        """Analyze import dependencies between files"""
        dependencies = {}
        
        for py_file in python_files:
            deps = set()
            
            try:
                with open(py_file, 'r') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module_name = alias.name
                            # Check if it's a local module
                            local_path = self._find_local_module(module_name)
                            if local_path:
                                deps.add(local_path)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            # Relative import
                            if node.level > 0:
                                module_path = self._resolve_relative_import(py_file, node.module, node.level)
                            else:
                                module_path = self._find_local_module(node.module)
                            
                            if module_path:
                                deps.add(module_path)
                
            except Exception as e:
                print(f"  ⚠️  Could not analyze {py_file}: {e}")
            
            dependencies[py_file] = deps
        
        return dependencies
    
    def _find_local_module(self, module_name: str) -> Optional[Path]:
        """Find local module file from import name"""
        # Convert module.submodule to path
        module_path = module_name.replace('.', '/')
        
        # Check for file
        possible_file = self.project_root / f"{module_path}.py"
        if possible_file.exists():
            return possible_file
        
        # Check for package
        possible_package = self.project_root / module_path / "__init__.py"
        if possible_package.exists():
            return possible_package
        
        return None
    
    def _resolve_relative_import(self, current_file: Path, module: str, level: int) -> Optional[Path]:
        """Resolve relative import to absolute path"""
        current_dir = current_file.parent
        
        # Go up 'level' directories
        for _ in range(level - 1):
            current_dir = current_dir.parent
        
        if module:
            module_path = module.replace('.', '/')
            possible_file = current_dir / f"{module_path}.py"
            if possible_file.exists():
                return possible_file
            
            possible_package = current_dir / module_path / "__init__.py"
            if possible_package.exists():
                return possible_package
        
        return None
    
    def _topological_sort(self, graph: Dict[Path, Set[Path]]) -> List[Path]:
        """Topological sort for dependency ordering"""
        visited = set()
        stack = []
        
        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, set()):
                visit(dep)
            stack.append(node)
        
        for node in graph:
            visit(node)
        
        return stack
    
    def _convert_file(self, py_file: Path):
        """Convert a single Python file to AIMacro"""
        rel_path = py_file.relative_to(self.project_root)
        output_file = self.output_dir / rel_path.with_suffix('.aimacro')
        
        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(py_file, 'r') as f:
                source = f.read()
            
            # Convert the source
            converted = self._convert_source_with_imports(source, py_file)
            
            # Write output
            with open(output_file, 'w') as f:
                f.write(converted)
            
            print(f"  ✅ {rel_path} -> {rel_path.with_suffix('.aimacro')}")
            self.converted_modules.add(str(rel_path))
            
        except Exception as e:
            print(f"  ❌ Failed to convert {rel_path}: {e}")
            self.failed_conversions.append((str(rel_path), str(e)))
    
    def _convert_source_with_imports(self, source: str, file_path: Path) -> str:
        """Convert source and handle imports"""
        lines = source.split('\n')
        result = []
        
        # First pass: convert imports
        import_section = []
        code_section = []
        in_imports = True
        
        for line in lines:
            stripped = line.strip()
            
            # Detect end of import section
            if in_imports and stripped and not stripped.startswith(('import ', 'from ', '#')):
                in_imports = False
            
            if in_imports and (stripped.startswith('import ') or stripped.startswith('from ')):
                # Convert import statement
                converted_import = self._convert_import(stripped, file_path)
                if converted_import:
                    import_section.append(converted_import)
            else:
                code_section.append(line)
        
        # Add AIMacro header
        result.append("# Generated from Python source")
        result.append("# Original file: " + str(file_path.relative_to(self.project_root)))
        result.append("")
        
        # Add converted imports
        if import_section:
            result.append("# Imports")
            result.extend(import_section)
            result.append("")
        
        # Convert the rest of the code
        from python_to_aimacro import PythonToAIMacroConverter
        converter = PythonToAIMacroConverter()
        code_str = '\n'.join(code_section)
        converted_code = converter.convert_source(code_str)
        
        result.append(converted_code)
        
        return '\n'.join(result)
    
    def _convert_import(self, import_line: str, current_file: Path) -> Optional[str]:
        """Convert Python import to AIMacro LibraryImport"""
        stripped = import_line.strip()
        
        # Parse import statement
        if stripped.startswith('import '):
            # import module1, module2
            modules = stripped[7:].split(',')
            results = []
            
            for module in modules:
                module = module.strip()
                if ' as ' in module:
                    module_name, alias = module.split(' as ')
                    module_name = module_name.strip()
                    alias = alias.strip()
                else:
                    module_name = module
                    alias = None
                
                # Check if it's stdlib
                if module_name in self.stdlib_mappings:
                    aimacro_module = self.stdlib_mappings[module_name]
                    results.append(f"LibraryImport {aimacro_module}")
                else:
                    # Local module
                    local_path = self._find_local_module(module_name)
                    if local_path:
                        rel_path = local_path.relative_to(self.project_root)
                        aimacro_path = str(rel_path.with_suffix('')).replace('/', '.')
                        results.append(f"LibraryImport {aimacro_path}")
            
            return '\n'.join(results) if results else None
        
        elif stripped.startswith('from '):
            # from module import item1, item2
            parts = stripped[5:].split(' import ')
            if len(parts) == 2:
                module_name = parts[0].strip()
                imports = parts[1].strip()
                
                # Handle relative imports
                if module_name.startswith('.'):
                    level = len(module_name) - len(module_name.lstrip('.'))
                    module_name = module_name.lstrip('.')
                    # Resolve relative path
                    module_path = self._resolve_relative_import(current_file, module_name, level)
                    if module_path:
                        rel_path = module_path.relative_to(self.project_root)
                        module_name = str(rel_path.with_suffix('')).replace('/', '.')
                
                # Check if it's stdlib
                if module_name in self.stdlib_mappings:
                    aimacro_module = self.stdlib_mappings[module_name]
                    return f"LibraryImport {aimacro_module}"
                else:
                    # Local module
                    return f"LibraryImport {module_name}"
        
        return None
    
    def _create_import_mapping(self):
        """Create a mapping file for imports"""
        mapping_file = self.output_dir / "import_mapping.json"
        
        mapping = {
            "stdlib_mappings": self.stdlib_mappings,
            "converted_modules": list(self.converted_modules),
            "failed_conversions": self.failed_conversions
        }
        
        with open(mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)
        
        print(f"\n📋 Import mapping saved to: {mapping_file}")
    
    def _create_project_manifest(self):
        """Create project manifest file"""
        manifest_file = self.output_dir / "project_manifest.aimacro"
        
        with open(manifest_file, 'w') as f:
            f.write("# AIMacro Project Manifest\n")
            f.write(f"# Generated from: {self.project_root}\n")
            f.write(f"# Total files converted: {len(self.converted_modules)}\n\n")
            
            f.write("# Main entry points\n")
            
            # Look for common entry points
            entry_points = ['main.aimacro', '__main__.aimacro', 'app.aimacro', 'run.aimacro']
            for entry in entry_points:
                entry_path = self.output_dir / entry
                if entry_path.exists():
                    f.write(f"EntryPoint {entry}\n")
            
            f.write("\n# Converted modules\n")
            for module in sorted(self.converted_modules):
                f.write(f"Module {module.replace('.py', '')}\n")
    
    def _print_summary(self):
        """Print conversion summary"""
        print("\n" + "="*60)
        print("📊 CONVERSION SUMMARY")
        print("="*60)
        print(f"✅ Successfully converted: {len(self.converted_modules)} files")
        
        if self.failed_conversions:
            print(f"❌ Failed conversions: {len(self.failed_conversions)}")
            for file, error in self.failed_conversions[:5]:
                print(f"   - {file}: {error}")
            if len(self.failed_conversions) > 5:
                print(f"   ... and {len(self.failed_conversions) - 5} more")
        
        print(f"\n📁 Output directory: {self.output_dir}")
        print(f"📋 Import mapping: {self.output_dir / 'import_mapping.json'}")
        print(f"📝 Project manifest: {self.output_dir / 'project_manifest.aimacro'}")

class SmartImportHandler:
    """Smart handling of Python imports for AIMacro conversion"""
    
    @staticmethod
    def create_aimacro_wrapper(python_module: str) -> str:
        """Create an AIMacro wrapper for a Python module"""
        wrapper = f"""
# AIMacro wrapper for Python module: {python_module}
# This provides compatibility layer for Python imports

LibraryImport Library.AIMacro

"""
        
        # Add common function mappings based on module
        if python_module == 'math':
            wrapper += """
# Math module compatibility
Function.sin = AIMacro.Math.sin
Function.cos = AIMacro.Math.cos
Function.tan = AIMacro.Math.tan
Function.sqrt = AIMacro.Math.sqrt
Function.pow = AIMacro.Math.pow
Function.exp = AIMacro.Math.exp
Function.log = AIMacro.Math.log
Function.floor = AIMacro.Math.floor
Function.ceil = AIMacro.Math.ceil
Function.pi = 3.14159265359
Function.e = 2.71828182846
"""
        
        elif python_module == 'random':
            wrapper += """
# Random module compatibility
Function.random = AIMacro.Random.random
Function.randint = AIMacro.Random.randint
Function.choice = AIMacro.Random.choice
Function.shuffle = AIMacro.Random.shuffle
Function.seed = AIMacro.Random.seed
"""
        
        elif python_module == 'os':
            wrapper += """
# OS module compatibility
Function.getcwd = AIMacro.System.getcwd
Function.chdir = AIMacro.System.chdir
Function.listdir = AIMacro.System.listdir
Function.mkdir = AIMacro.System.mkdir
Function.remove = AIMacro.System.remove
Function.path.exists = AIMacro.System.path_exists
Function.path.join = AIMacro.System.path_join
"""
        
        return wrapper

def main():
    parser = argparse.ArgumentParser(
        description='Batch convert Python projects to AIMacro'
    )
    
    parser.add_argument('project_root', help='Root directory of Python project')
    parser.add_argument('output_dir', help='Output directory for AIMacro files')
    parser.add_argument('--create-wrappers', action='store_true',
                       help='Create compatibility wrappers for Python stdlib')
    parser.add_argument('--single-file', action='store_true',
                       help='Convert single file with dependency resolution')
    
    args = parser.parse_args()
    
    if args.single_file:
        # Single file mode with smart import handling
        from python_to_aimacro import PythonToAIMacroConverter
        converter = PythonToAIMacroConverter()
        converter.convert_file(args.project_root, args.output_dir)
    else:
        # Full project conversion
        converter = PythonProjectConverter(args.project_root, args.output_dir)
        converter.convert_project()
        
        if args.create_wrappers:
            # Create stdlib wrappers
            wrapper_dir = Path(args.output_dir) / 'stdlib_wrappers'
            wrapper_dir.mkdir(exist_ok=True)
            
            handler = SmartImportHandler()
            for module in ['math', 'random', 'os', 'sys', 'json']:
                wrapper = handler.create_aimacro_wrapper(module)
                wrapper_file = wrapper_dir / f"{module}.aimacro"
                with open(wrapper_file, 'w') as f:
                    f.write(wrapper)
            
            print(f"\n✨ Created stdlib wrappers in: {wrapper_dir}")

if __name__ == "__main__":
    main()
