from typing import List, Dict, Any
from intelligence.models import SymbolRecord
from intelligence.parsers.parser_registry import ParserRegistry

class SymbolIndexer:
    def __init__(self):
        self.symbols: List[SymbolRecord] = []
        # Fast lookup maps
        self.by_file: Dict[str, List[SymbolRecord]] = {}
        self.by_name: Dict[str, List[SymbolRecord]] = {}

    def index_file(self, file_path: str, content: str) -> None:
        """Parse file content and add its symbols to the global index."""
        # Clean existing index entries for this file to support incremental updates
        self.remove_file(file_path)

        parser = ParserRegistry.get_parser(file_path)
        parser.load(content, file_path)
        if parser.parse():
            file_symbols = parser.get_symbols()
            self.by_file[file_path] = file_symbols
            for sym in file_symbols:
                self.symbols.append(sym)
                if sym.name not in self.by_name:
                    self.by_name[sym.name] = []
                self.by_name[sym.name].append(sym)

    def remove_file(self, file_path: str) -> None:
        """Remove a file's symbols from the global index."""
        if file_path in self.by_file:
            old_symbols = self.by_file.pop(file_path)
            old_names = {s.name for s in old_symbols}
            
            # Remove from flat list
            self.symbols = [s for s in self.symbols if s.file_path != file_path]
            
            # Remove from by_name lookup
            for name in old_names:
                if name in self.by_name:
                    self.by_name[name] = [s for s in self.by_name[name] if s.file_path != file_path]
                    if not self.by_name[name]:
                        self.by_name.pop(name)

    def get_all_symbols(self) -> List[SymbolRecord]:
        return self.symbols

    def get_file_symbols(self, file_path: str) -> List[SymbolRecord]:
        return self.by_file.get(file_path, [])

    def get_symbol_by_name(self, name: str) -> List[SymbolRecord]:
        return self.by_name.get(name, [])
