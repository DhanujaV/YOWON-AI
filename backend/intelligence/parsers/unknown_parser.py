import re
import hashlib
from typing import List, Dict, Any
from intelligence.models import SymbolRecord
from intelligence.parsers.base_parser import BaseParser

class UnknownParser(BaseParser):
    def parse(self) -> bool:
        # Unknown files don't build a formal AST, but load successfully
        return True

    def get_symbols(self) -> List[SymbolRecord]:
        symbols = []
        # Fallback regex search for class and function declarations in other languages
        # Class declaration: class Foo, struct Foo, interface Foo
        class_rx = re.compile(r'\b(class|struct|interface|type)\s+([A-Za-z0-9_]+)', re.MULTILINE)
        # Function declaration: function foo(), func foo(), void foo()
        func_rx = re.compile(r'\b(function|func|void|int|string|def)\s+([A-Za-z0-9_]+)\s*\(', re.MULTILINE)

        for line_no, line in enumerate(self.lines, 1):
            for match in class_rx.finditer(line):
                symbols.append(SymbolRecord(
                    name=match.group(2),
                    type="class",
                    file_path=self.file_path,
                    line_start=line_no,
                    line_end=line_no,
                    column_start=match.start(2),
                    column_end=match.end(2)
                ))
            for match in func_rx.finditer(line):
                symbols.append(SymbolRecord(
                    name=match.group(2),
                    type="function",
                    file_path=self.file_path,
                    line_start=line_no,
                    line_end=line_no,
                    column_start=match.start(2),
                    column_end=match.end(2)
                ))
        return symbols

    def get_imports(self) -> List[str]:
        imports = []
        # Match typical import statements: import "foo", require("foo"), include "foo"
        import_rx = re.compile(r'\b(import|require|include|using)\s+["\'<]?([A-Za-z0-9_\-\./]+)["\'>]?', re.IGNORECASE)
        for line in self.lines:
            for match in import_rx.finditer(line):
                imports.append(match.group(2))
        return list(set(imports))

    def get_complexity_metrics(self) -> Dict[str, Any]:
        # Estimate metrics based on regexes
        # Cyclomatic complexity: 1 + count of if/for/while/switch/catch/&&/||
        branch_rx = re.compile(r'\b(if|for|while|switch|catch|else if)\b|&&|\|\|')
        cyclo = 1
        funcs = 0
        classes = 0
        for line in self.lines:
            cyclo += len(branch_rx.findall(line))
            if "class " in line or "struct " in line or "interface " in line:
                classes += 1
            if "function " in line or "def " in line or "func " in line:
                funcs += 1

        return {
            "function_count": funcs,
            "class_count": classes,
            "cyclomatic_complexity": min(100, cyclo),
            "cognitive_complexity": min(100, cyclo - 1),
            "nesting_depth": min(10, cyclo // 3)
        }

    def scan_unsafe_apis(self) -> List[Dict[str, Any]]:
        unsafe = []
        # Scan for common unsafe commands in general scripts: eval(), exec(), system(), etc.
        unsafe_rx = re.compile(r'\b(eval|exec|system|popen)\s*\(', re.IGNORECASE)
        for line_no, line in enumerate(self.lines, 1):
            for match in unsafe_rx.finditer(line):
                unsafe.append({
                    "api": match.group(1),
                    "line_start": line_no,
                    "line_end": line_no,
                    "column_start": match.start(1),
                    "column_end": match.end(1),
                    "description": f"Unsafe API call: {match.group(1)}()"
                })
        return unsafe
