from typing import Dict, List
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder

class CallGraphBuilder(BaseGraphBuilder):
    def build(self, file_imports: Dict[str, List[str]], files: List[str]) -> None:
        """Constructs inter-module imports/dependency Call Graph between source files."""
        self.nodes = []
        self.edges = []

        # Create lookup set of file basenames and paths
        file_set = set(files)
        # Create a mapping of imported names to files (e.g., "utils" -> "src/utils.py")
        name_to_file = {}
        for f in files:
            name_to_file[f] = f
            basename = f.split("/")[-1].split(".")[0]
            name_to_file[basename] = f
            if "/" in f:
                rel_parts = f.replace(".py", "").replace(".js", "").replace(".ts", "").replace("/", ".")
                name_to_file[rel_parts] = f

        # 1. Add file nodes
        for f in files:
            # Only include source code files in the call graph
            if f.split(".")[-1] in ("py", "js", "ts", "jsx", "tsx"):
                self.nodes.append(GraphNode(
                    id=f,
                    label=f.split("/")[-1],
                    type="file",
                    metadata={"path": f}
                ))

        node_ids = {n.id for n in self.nodes}

        # 2. Add edges based on imports resolving to files
        for f, imports in file_imports.items():
            if f not in node_ids:
                continue
            for imp in imports:
                # Try to resolve import name to a repository file
                resolved_file = name_to_file.get(imp)
                if not resolved_file:
                    # Check if any file path contains the import string
                    for fpath in files:
                        if imp.replace(".", "/") in fpath and fpath != f:
                            resolved_file = fpath
                            break
                
                if resolved_file and resolved_file in node_ids and resolved_file != f:
                    self.edges.append(GraphEdge(
                        source=f,
                        target=resolved_file,
                        label="imports"
                    ))
