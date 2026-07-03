from abc import ABC, abstractmethod
from typing import List, Dict, Any
from intelligence.models import SymbolRecord

class BaseParser(ABC):
    def __init__(self):
        self.file_content = ""
        self.file_path = ""
        self.lines = []

    def load(self, file_content: str, file_path: str) -> None:
        self.file_content = file_content
        self.file_path = file_path
        self.lines = file_content.splitlines()

    @abstractmethod
    def parse(self) -> bool:
        """Parse file content and build AST tree. Return True if successful."""
        pass

    @abstractmethod
    def get_symbols(self) -> List[SymbolRecord]:
        """Extract and return list of SymbolRecords."""
        pass

    @abstractmethod
    def get_imports(self) -> List[str]:
        """Extract and return list of imported modules/files."""
        pass

    @abstractmethod
    def get_complexity_metrics(self) -> Dict[str, Any]:
        """Return dict with function_count, class_count, cyclomatic_complexity, cognitive_complexity, nesting_depth."""
        pass

    @abstractmethod
    def scan_unsafe_apis(self) -> List[Dict[str, Any]]:
        """Return list of unsafe API usages (e.g. eval, subprocess) with lines/columns."""
        pass
