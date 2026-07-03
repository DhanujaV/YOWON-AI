from typing import Dict, Type
from intelligence.parsers.base_parser import BaseParser
from intelligence.parsers.python_parser import PythonParser
from intelligence.parsers.javascript_parser import JavaScriptParser
from intelligence.parsers.typescript_parser import TypeScriptParser
from intelligence.parsers.unknown_parser import UnknownParser

class ParserRegistry:
    _registry: Dict[str, Type[BaseParser]] = {
        ".py": PythonParser,
        ".js": JavaScriptParser,
        ".jsx": JavaScriptParser,
        ".ts": TypeScriptParser,
        ".tsx": TypeScriptParser,
    }

    @classmethod
    def register(cls, extensions: list[str]):
        """Allows registering custom parsers dynamically."""
        def decorator(parser_cls: Type[BaseParser]):
            for ext in extensions:
                cls._registry[ext.lower()] = parser_cls
            return parser_cls
        return decorator

    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        ext = ""
        if "." in file_path:
            ext = "." + file_path.rsplit(".", 1)[-1].lower()
        parser_cls = cls._registry.get(ext, UnknownParser)
        return parser_cls()
