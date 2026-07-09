import ast
from typing import List, Dict, Any, Optional
from intelligence.models import SymbolRecord
from intelligence.parsers.base_parser import BaseParser

class PythonParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.tree = None

    def parse(self) -> bool:
        try:
            self.tree = ast.parse(self.file_content, filename=self.file_path)
            return True
        except Exception:
            return False

    def get_symbols(self) -> List[SymbolRecord]:
        if not self.tree:
            return []
        
        symbols = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sym_type = "method" if getattr(node, "is_method", False) else "function"
                
                # Check for API decorators
                decorators = []
                for dec in node.decorator_list:
                    dec_name = self._get_decorator_name(dec)
                    if dec_name:
                        decorators.append(dec_name)
                
                route_info = self._get_route_info(node)
                if route_info:
                    sym_type = "route"

                symbols.append(SymbolRecord(
                    name=node.name,
                    type=sym_type,
                    file_path=self.file_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    column_start=node.col_offset,
                    column_end=getattr(node, "end_col_offset", node.col_offset),
                    relationships=[{"type": "decorator", "name": dec} for dec in decorators]
                ))
            elif isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    base_name = self._get_name_from_node(base)
                    if base_name:
                        bases.append(base_name)
                
                is_db_model = any(b in ("Base", "Model", "DeclarativeBase") or "model" in b.lower() for b in bases)
                sym_type = "model" if is_db_model else "class"

                # Mark child functions as methods
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        child.is_method = True

                symbols.append(SymbolRecord(
                    name=node.name,
                    type=sym_type,
                    file_path=self.file_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    column_start=node.col_offset,
                    column_end=getattr(node, "end_col_offset", node.col_offset),
                    relationships=[{"type": "extends", "target": b} for b in bases]
                ))
        return symbols

    def get_imports(self) -> List[str]:
        if not self.tree:
            return []
        
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return list(set(imports))

    def get_complexity_metrics(self) -> Dict[str, Any]:
        if not self.tree:
            return {
                "function_count": 0,
                "class_count": 0,
                "cyclomatic_complexity": 1,
                "cognitive_complexity": 0,
                "nesting_depth": 0
            }

        function_count = 0
        class_count = 0
        cyclomatic = 1
        cognitive = 0
        max_depth = 0

        # Calculate Cyclomatic Complexity & count functions/classes
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Try, ast.And, ast.Or)):
                cyclomatic += 1

        # Calculate Cognitive Complexity & Nesting Depth
        class CognitiveVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 0
                self.current_nesting = 0
                self.max_nesting = 0

            def visit_If(self, node):
                self.complexity += 1 + self.current_nesting
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1

            def visit_For(self, node):
                self.complexity += 1 + self.current_nesting
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1

            def visit_While(self, node):
                self.complexity += 1 + self.current_nesting
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1

            def visit_ExceptHandler(self, node):
                self.complexity += 1 + self.current_nesting
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1

        visitor = CognitiveVisitor()
        visitor.visit(self.tree)
        cognitive = visitor.complexity
        max_depth = visitor.max_nesting

        return {
            "function_count": function_count,
            "class_count": class_count,
            "cyclomatic_complexity": cyclomatic,
            "cognitive_complexity": cognitive,
            "nesting_depth": max_depth
        }

    def scan_unsafe_apis(self) -> List[Dict[str, Any]]:
        if not self.tree:
            return []

        unsafe_usages = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                func_name = self._get_name_from_node(node.func)
                if func_name in ("eval", "exec", "subprocess.run", "subprocess.Popen", "subprocess.call", "os.system"):
                    unsafe_usages.append({
                        "api": func_name,
                        "line_start": node.lineno,
                        "line_end": getattr(node, "end_lineno", node.lineno),
                        "column_start": node.col_offset,
                        "column_end": getattr(node, "end_col_offset", node.col_offset),
                        "description": f"Unsafe API call: {func_name}()"
                    })
        return unsafe_usages

    def _get_name_from_node(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_name_from_node(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
            return node.attr
        return ""

    def _get_decorator_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Call):
            return self._get_name_from_node(node.func)
        return self._get_name_from_node(node)

    def _get_route_info(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[str]:
        for dec in node.decorator_list:
            name = self._get_decorator_name(dec)
            if any(term in name.lower() for term in ("route", "get", "post", "put", "delete", "patch", "api")):
                return name
        return None
