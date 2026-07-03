import sys
sys.path.insert(0, ".")
from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs

js_lang = Language(tsjs.language())
parser = Parser(js_lang)
tree = parser.parse(b"const a = 1;")
print("Root node type:", tree.root_node.type)
for child in tree.root_node.children:
    print("Child type:", child.type)
