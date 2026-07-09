from typing import List, Dict, Any
try:
    from tree_sitter import Language, Parser
    import tree_sitter_javascript as tsjs
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _TREE_SITTER_AVAILABLE = False
    Language = None
    Parser = None
    tsjs = None
from intelligence.models import SymbolRecord
from intelligence.parsers.base_parser import BaseParser

class JavaScriptParser(BaseParser):
    def __init__(self):
        super().__init__()
        if _TREE_SITTER_AVAILABLE:
            self.js_lang = Language(tsjs.language())
            self.parser = Parser(self.js_lang)
        else:
            self.js_lang = None
            self.parser = None
        self.tree = None

    def parse(self) -> bool:
        try:
            self.tree = self.parser.parse(bytes(self.file_content, "utf-8"))
            return True
        except Exception:
            return False

    def get_symbols(self) -> List[SymbolRecord]:
        if not self.tree:
            return []

        symbols = []
        
        def traverse(node):
            if node.type in ("class_declaration", "class"):
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node) if name_node else "AnonymousClass"
                symbols.append(SymbolRecord(
                    name=name,
                    type="class",
                    file_path=self.file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    column_start=node.start_point[1],
                    column_end=node.end_point[1],
                    relationships=[]
                ))
            elif node.type in ("function_declaration", "method_definition"):
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node) if name_node else "anonymous"
                sym_type = "method" if node.type == "method_definition" else "function"
                
                # Check if it might be an API route in Express/Node
                # (rough heuristic: method names or parent calls)
                symbols.append(SymbolRecord(
                    name=name,
                    type=sym_type,
                    file_path=self.file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    column_start=node.start_point[1],
                    column_end=node.end_point[1],
                    relationships=[]
                ))
            
            for child in node.children:
                traverse(child)

        traverse(self.tree.root_node)
        return symbols

    def get_imports(self) -> List[str]:
        if not self.tree:
            return []

        imports = []
        
        def traverse(node):
            if node.type == "import_statement":
                # Find source string
                source_node = node.child_by_field_name("source")
                if source_node:
                    imports.append(self._clean_module_name(self._node_text(source_node)))
            elif node.type == "call_expression":
                # Check for require("module")
                func_node = node.child_by_field_name("function")
                if func_node and self._node_text(func_node) == "require":
                    args = node.child_by_field_name("arguments")
                    if args and len(args.children) > 1:
                        # args.children[1] is the first argument (skipping '(')
                        mod_name = self._node_text(args.children[1])
                        imports.append(self._clean_module_name(mod_name))
            
            for child in node.children:
                traverse(child)

        traverse(self.tree.root_node)
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

        counts = {"funcs": 0, "classes": 0, "cyclo": 1, "cog": 0, "max_nest": 0}
        
        def traverse(node, nesting=0):
            if node.type in ("function_declaration", "method_definition", "arrow_function", "function"):
                counts["funcs"] += 1
            elif node.type in ("class_declaration", "class"):
                counts["classes"] += 1
            
            is_branch = node.type in (
                "if_statement", "for_in_statement", "for_of_statement", "for_statement",
                "while_statement", "do_statement", "catch_clause", "ternary_expression"
            )
            
            if is_branch:
                counts["cyclo"] += 1
                counts["cog"] += 1 + nesting
                nesting += 1
                counts["max_nest"] = max(counts["max_nest"], nesting)
            
            if node.type == "binary_expression":
                op_node = node.child_by_field_name("operator")
                if op_node and self._node_text(op_node) in ("&&", "||"):
                    counts["cyclo"] += 1

            for child in node.children:
                traverse(child, nesting)

        traverse(self.tree.root_node)
        return {
            "function_count": counts["funcs"],
            "class_count": counts["classes"],
            "cyclomatic_complexity": counts["cyclo"],
            "cognitive_complexity": counts["cog"],
            "nesting_depth": counts["max_nest"]
        }

    def scan_unsafe_apis(self) -> List[Dict[str, Any]]:
        if not self.tree:
            return []

        unsafe_usages = []

        def traverse(node):
            if node.type == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node:
                    func_name = self._node_text(func_node)
                    if func_name in ("eval", "exec", "child_process.exec", "child_process.spawn"):
                        unsafe_usages.append({
                            "api": func_name,
                            "line_start": node.start_point[0] + 1,
                            "line_end": node.end_point[0] + 1,
                            "column_start": node.start_point[1],
                            "column_end": node.end_point[1],
                            "description": f"Unsafe API call: {func_name}()"
                        })
            for child in node.children:
                traverse(child)

        traverse(self.tree.root_node)
        return unsafe_usages

    def _node_text(self, node) -> str:
        # Extract text from source using node start and end bytes
        return self.file_content[node.start_byte:node.end_byte]

    def _clean_module_name(self, name: str) -> str:
        # Strip quotes
        return name.strip("\"'")
