try:
    from tree_sitter import Language, Parser
    import tree_sitter_typescript as tsts
    _TS_AVAILABLE = True
except ImportError:
    _TS_AVAILABLE = False
    Language = None
    Parser = None
    tsts = None
from intelligence.parsers.javascript_parser import JavaScriptParser

class TypeScriptParser(JavaScriptParser):
    def __init__(self):
        super().__init__()
        # Load TypeScript language definition (only when tree-sitter available)
        if _TS_AVAILABLE:
            self.ts_lang = Language(tsts.language_typescript())
            self.parser = Parser(self.ts_lang)
