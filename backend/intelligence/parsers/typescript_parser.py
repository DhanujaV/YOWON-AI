from typing import List, Dict, Any
from tree_sitter import Language, Parser
import tree_sitter_typescript as tsts
from intelligence.parsers.javascript_parser import JavaScriptParser

class TypeScriptParser(JavaScriptParser):
    def __init__(self):
        super().__init__()
        # Load TypeScript language definition
        self.ts_lang = Language(tsts.language_typescript())
        self.parser = Parser(self.ts_lang)
