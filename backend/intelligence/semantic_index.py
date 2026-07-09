"""
semantic_index.py — Shared single-pass semantic index.

Built ONCE from RepositoryScan. Every engine (ArchitectureEngine, EvidenceEngine,
KnowledgeGraphBuilder, DependencyAnalyzer, TechnologyDetector) consumes this.
No additional file reads occur after SemanticIndex is built.
"""
from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set

from intelligence.models import SymbolRecord
from intelligence.repository_scan import RepositoryScan

logger = logging.getLogger(__name__)


@dataclass
class TechDetection:
    """A detected technology with confidence score and evidence sources."""
    name: str
    version: Optional[str] = None
    confidence: float = 0.0          # 0.0–1.0
    category: str = "FRAMEWORK"      # FRAMEWORK | LANGUAGE | TOOL | DATABASE | ML | CLOUD | RUNTIME
    sources: List[str] = field(default_factory=list)  # e.g. ["requirements.txt", "import", "decorator"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "confidence": round(self.confidence, 3),
            "category": self.category,
            "sources": self.sources,
        }


@dataclass
class RouteRecord:
    """An API endpoint detected from AST decorators."""
    method: str           # GET | POST | PUT | DELETE | PATCH | ANY
    path: Optional[str]   # URL path if extractable
    function_name: str
    file_path: str
    line_start: int
    framework: str = "fastapi"  # fastapi | flask | django | express


@dataclass
class ModelRecord:
    """An ORM/Pydantic model class detected from AST."""
    name: str
    file_path: str
    line_start: int
    base_classes: List[str] = field(default_factory=list)
    model_type: str = "orm"  # orm | pydantic | dataclass | schema


@dataclass
class ServiceRecord:
    """A service/agent class detected from AST class analysis."""
    name: str
    file_path: str
    line_start: int
    service_type: str = "service"  # service | agent | crew | worker | controller


@dataclass
class SemanticIndex:
    """
    Complete semantic knowledge extracted from the repository in a single pass.

    Built from RepositoryScan using AST parsers + manifest parsers.
    All engines share this index — zero additional I/O after build().
    """
    # AST-derived
    symbols: Dict[str, List[SymbolRecord]] = field(default_factory=dict)  # file_path → symbols
    imports: Dict[str, List[str]] = field(default_factory=dict)           # file_path → module names
    routes: List[RouteRecord] = field(default_factory=list)
    models: List[ModelRecord] = field(default_factory=list)
    agents_and_services: List[ServiceRecord] = field(default_factory=list)

    # Configuration / environment
    env_vars: Dict[str, str] = field(default_factory=dict)       # var_name → file_path where used
    config_files: List[str] = field(default_factory=list)

    # Multi-language dependencies
    python_deps: Dict[str, str] = field(default_factory=dict)    # dep → version
    node_deps: Dict[str, str] = field(default_factory=dict)
    go_deps: Dict[str, str] = field(default_factory=dict)
    rust_deps: Dict[str, str] = field(default_factory=dict)
    java_deps: Dict[str, str] = field(default_factory=dict)
    csharp_deps: Dict[str, str] = field(default_factory=dict)
    docker_images: List[str] = field(default_factory=list)
    docker_services: List[str] = field(default_factory=list)

    # Detected technologies with confidence
    technologies: List[TechDetection] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)

    # Aggregate stats (for diagnostics)
    total_files: int = 0
    total_directories: int = 0
    total_loc: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_ast_nodes: int = 0
    total_imports: int = 0
    languages_detected: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def build(cls, scan: RepositoryScan) -> "SemanticIndex":
        """
        Single pass over all repository files to populate every index.
        Uses Python's built-in ast module for .py files and regex for JS/TS.
        """
        idx = cls()
        idx.total_files = len(scan.files)
        idx._count_dirs(scan)
        idx._parse_dependency_manifests(scan)
        idx._parse_source_files(scan)
        idx._detect_technologies(scan)
        idx._detect_capabilities(scan)
        idx._count_aggregate_stats()
        return idx

    # ──────────────────────────────────────────────────────────────────────────
    # Internal builders
    # ──────────────────────────────────────────────────────────────────────────

    def _count_dirs(self, scan: RepositoryScan) -> None:
        dirs: Set[str] = set()
        for f in scan.files:
            parts = f.rsplit("/", 1)
            if len(parts) == 2:
                dirs.add(parts[0])
        self.total_directories = len(dirs)

    def _parse_dependency_manifests(self, scan: RepositoryScan) -> None:
        """Parse all detected dependency manifests."""
        for fpath, content in scan.dependency_manifests.items():
            basename = fpath.split("/")[-1].lower()
            try:
                if basename == "requirements.txt":
                    self.python_deps.update(self._parse_requirements_txt(content))
                elif basename in ("pyproject.toml",):
                    self.python_deps.update(self._parse_pyproject_toml(content))
                elif basename == "pipfile":
                    self.python_deps.update(self._parse_pipfile(content))
                elif basename == "package.json":
                    self.node_deps.update(self._parse_package_json(content))
                elif basename == "go.mod":
                    self.go_deps.update(self._parse_go_mod(content))
                elif basename == "cargo.toml":
                    self.rust_deps.update(self._parse_cargo_toml(content))
                elif basename in ("pom.xml",):
                    self.java_deps.update(self._parse_pom_xml(content))
                elif basename == "build.gradle" or basename == "build.gradle.kts":
                    self.java_deps.update(self._parse_gradle(content))
                elif fpath.endswith((".csproj", ".fsproj")):
                    self.csharp_deps.update(self._parse_csproj(content))
                elif basename in ("dockerfile",):
                    imgs = self._parse_dockerfile(content)
                    self.docker_images.extend(imgs)
                elif "docker-compose" in basename:
                    self._parse_docker_compose(fpath, content)
            except Exception as e:
                self.warnings.append(f"[SemanticIndex] Failed to parse {fpath}: {e}")

        # Merge raw_dependencies from snapshot as fallback
        if scan.raw_dependencies and not self.python_deps:
            self.python_deps.update(scan.raw_dependencies)

    def _parse_source_files(self, scan: RepositoryScan) -> None:
        """Parse each source file for symbols, imports, routes, models, services."""
        env_pattern = re.compile(
            r'(?:os\.environ\.get|os\.getenv|os\.environ\[|dotenv_values)\s*\(\s*["\']([A-Z0-9_]+)["\']'
        )
        config_indicators = (
            "config", "settings", "env", ".env", ".toml", ".yaml", ".yml",
            "configuration", "constants"
        )

        for fpath in scan.files:
            content = scan.file_contents.get(fpath, "")
            ext = fpath.rsplit(".", 1)[-1].lower() if "." in fpath else ""

            # Track languages
            lang_map = {
                "py": "Python", "js": "JavaScript", "ts": "TypeScript",
                "jsx": "JavaScript", "tsx": "TypeScript", "go": "Go",
                "rs": "Rust", "java": "Java", "cs": "C#", "rb": "Ruby",
            }
            lang = lang_map.get(ext)
            if lang and lang not in self.languages_detected:
                self.languages_detected.append(lang)

            # Detect config files
            fname_lower = fpath.lower()
            if any(ind in fname_lower for ind in config_indicators):
                if fpath not in self.config_files:
                    self.config_files.append(fpath)

            # Count LOC
            if content:
                self.total_loc += len(content.splitlines())

            # Scan env vars
            if content:
                for var in env_pattern.findall(content):
                    if var not in self.env_vars:
                        self.env_vars[var] = fpath

            # Language-specific AST parsing
            if ext == "py" and content:
                self._parse_python_file(fpath, content)
            elif ext in ("js", "ts", "jsx", "tsx") and content:
                self._parse_js_ts_file(fpath, content, ext)

    def _parse_python_file(self, fpath: str, content: str) -> None:
        """Parse Python file using stdlib AST."""
        try:
            tree = ast.parse(content, filename=fpath)
        except SyntaxError:
            self.warnings.append(f"[SemanticIndex] Syntax error in {fpath}")
            return

        file_symbols: List[SymbolRecord] = []
        file_imports: List[str] = []

        # Collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    file_imports.append(node.module.split(".")[0])

        self.imports[fpath] = list(set(file_imports))
        self.total_imports += len(file_imports)

        # Walk for classes and functions
        ROUTE_DECORATORS = {"get", "post", "put", "delete", "patch", "head", "options"}
        ORM_BASES = {"Base", "DeclarativeBase", "DeclarativeMeta", "Model", "Document"}
        PYDANTIC_BASES = {"BaseModel", "BaseSettings", "RootModel"}
        AGENT_INDICATORS = {"Agent", "CrewAgent", "LlmAgent", "BaseAgent"}
        SERVICE_PATTERNS = ("service", "handler", "manager", "processor", "controller", "repository", "repo")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.total_classes += 1
                bases = [self._name_from_node(b) for b in node.bases]
                bases = [b for b in bases if b]

                # Determine class role
                is_orm = any(b in ORM_BASES or "model" in b.lower() for b in bases)
                is_pydantic = any(b in PYDANTIC_BASES for b in bases)
                is_agent = any(b in AGENT_INDICATORS for b in bases) or any(
                    kw in node.name.lower() for kw in ("agent", "crew")
                )
                is_service = any(p in node.name.lower() for p in SERVICE_PATTERNS)

                sym_type = "model" if (is_orm or is_pydantic) else "class"
                sym = SymbolRecord(
                    name=node.name, type=sym_type, file_path=fpath,
                    line_start=node.lineno, line_end=getattr(node, "end_lineno", node.lineno),
                    column_start=node.col_offset, column_end=0,
                    relationships=[{"type": "extends", "target": b} for b in bases]
                )
                file_symbols.append(sym)

                if is_orm:
                    self.models.append(ModelRecord(
                        name=node.name, file_path=fpath, line_start=node.lineno,
                        base_classes=bases, model_type="orm"
                    ))
                elif is_pydantic:
                    self.models.append(ModelRecord(
                        name=node.name, file_path=fpath, line_start=node.lineno,
                        base_classes=bases, model_type="pydantic"
                    ))

                if is_agent:
                    self.agents_and_services.append(ServiceRecord(
                        name=node.name, file_path=fpath, line_start=node.lineno,
                        service_type="agent"
                    ))
                elif is_service:
                    self.agents_and_services.append(ServiceRecord(
                        name=node.name, file_path=fpath, line_start=node.lineno,
                        service_type="service"
                    ))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.total_functions += 1
                # Check for route decorators
                for dec in node.decorator_list:
                    dec_name = self._name_from_node(dec if not isinstance(dec, ast.Call) else dec.func)
                    if dec_name:
                        parts = dec_name.lower().split(".")
                        method = next((p for p in parts if p in ROUTE_DECORATORS), None)
                        if method:
                            # Extract path from decorator args
                            path_val = None
                            if isinstance(dec, ast.Call) and dec.args:
                                try:
                                    path_val = ast.literal_eval(dec.args[0])
                                except Exception:
                                    pass
                            self.routes.append(RouteRecord(
                                method=method.upper(), path=path_val,
                                function_name=node.name, file_path=fpath,
                                line_start=node.lineno, framework="fastapi"
                            ))

                sym = SymbolRecord(
                    name=node.name,
                    type="route" if any(r.function_name == node.name and r.file_path == fpath
                                        for r in self.routes) else "function",
                    file_path=fpath,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    column_start=node.col_offset,
                    column_end=0,
                    relationships=[]
                )
                file_symbols.append(sym)

        self.symbols[fpath] = file_symbols

    def _parse_js_ts_file(self, fpath: str, content: str, ext: str) -> None:
        """Parse JS/TS file using regex (tree-sitter not available in all envs)."""
        file_imports: List[str] = []
        file_symbols: List[SymbolRecord] = []

        # Imports: import X from 'module' or require('module')
        import_re = re.compile(r'import\s+.*?from\s+["\']([^"\'.][^"\']+)["\']')
        require_re = re.compile(r'require\s*\(\s*["\']([^"\'.][^"\']+)["\']\s*\)')
        for m in import_re.findall(content):
            file_imports.append(m.split("/")[0].lstrip("@").split("/")[0] if m.startswith("@") else m.split("/")[0])
        for m in require_re.findall(content):
            file_imports.append(m.split("/")[0])

        self.imports[fpath] = list(set(file_imports))
        self.total_imports += len(file_imports)

        # Classes
        class_re = re.compile(r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)', re.MULTILINE)
        for i, m in enumerate(class_re.finditer(content)):
            self.total_classes += 1
            line = content[:m.start()].count("\n") + 1
            file_symbols.append(SymbolRecord(
                name=m.group(1), type="class", file_path=fpath,
                line_start=line, line_end=line, column_start=0, column_end=0,
                relationships=[]
            ))

        # Functions / arrow functions
        func_re = re.compile(
            r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)|'
            r'^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(',
            re.MULTILINE
        )
        for m in func_re.finditer(content):
            self.total_functions += 1
            name = m.group(1) or m.group(2)
            if name:
                line = content[:m.start()].count("\n") + 1
                file_symbols.append(SymbolRecord(
                    name=name, type="function", file_path=fpath,
                    line_start=line, line_end=line, column_start=0, column_end=0,
                    relationships=[]
                ))

        # Express routes
        route_re = re.compile(r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')
        for m in route_re.finditer(content):
            line = content[:m.start()].count("\n") + 1
            self.routes.append(RouteRecord(
                method=m.group(1).upper(), path=m.group(2),
                function_name=f"route_{m.group(1)}_{m.group(2).replace('/', '_')}",
                file_path=fpath, line_start=line, framework="express"
            ))

        self.symbols[fpath] = file_symbols

    def _detect_technologies(self, scan: RepositoryScan) -> None:
        """Build TechDetection list from all collected data."""
        tech_map: Dict[str, TechDetection] = {}

        def add_tech(name: str, version: Optional[str], confidence: float,
                     category: str, source: str) -> None:
            key = name.lower()
            if key not in tech_map:
                tech_map[key] = TechDetection(
                    name=name, version=version, confidence=confidence,
                    category=category, sources=[source]
                )
            else:
                t = tech_map[key]
                if source not in t.sources:
                    t.sources.append(source)
                # Raise confidence if confirmed from multiple sources
                t.confidence = min(1.0, max(t.confidence, confidence) + 0.02 * len(t.sources))
                if version and not t.version:
                    t.version = version

        # From dependency manifests
        PYTHON_TECH = {
            "fastapi": ("FastAPI", "FRAMEWORK"), "flask": ("Flask", "FRAMEWORK"),
            "django": ("Django", "FRAMEWORK"), "sqlalchemy": ("SQLAlchemy", "DATABASE"),
            "langchain": ("LangChain", "ML"), "crewai": ("CrewAI", "ML"),
            "openai": ("OpenAI", "ML"), "anthropic": ("Anthropic", "ML"),
            "ollama": ("Ollama", "ML"), "chromadb": ("ChromaDB", "DATABASE"),
            "pydantic": ("Pydantic", "FRAMEWORK"), "celery": ("Celery", "TOOL"),
            "redis": ("Redis", "DATABASE"), "aiohttp": ("aiohttp", "FRAMEWORK"),
            "httpx": ("HTTPX", "TOOL"), "pytest": ("Pytest", "TOOL"),
            "uvicorn": ("Uvicorn", "RUNTIME"), "gunicorn": ("Gunicorn", "RUNTIME"),
            "alembic": ("Alembic", "TOOL"),
        }
        for dep, version in self.python_deps.items():
            dl = dep.lower()
            if dl in PYTHON_TECH:
                name, cat = PYTHON_TECH[dl]
                add_tech(name, version, 0.99, cat, "requirements.txt")
        if self.python_deps:
            add_tech("Python", None, 0.99, "LANGUAGE", "requirements.txt")

        NODE_TECH = {
            "react": ("React", "FRAMEWORK"), "vue": ("Vue.js", "FRAMEWORK"),
            "angular": ("Angular", "FRAMEWORK"), "next": ("Next.js", "FRAMEWORK"),
            "vite": ("Vite", "TOOL"), "typescript": ("TypeScript", "LANGUAGE"),
            "express": ("Express.js", "FRAMEWORK"), "tailwindcss": ("Tailwind CSS", "TOOL"),
            "axios": ("Axios", "TOOL"), "@tanstack/react-query": ("TanStack Query", "TOOL"),
            "framer-motion": ("Framer Motion", "TOOL"), "jest": ("Jest", "TOOL"),
            "vitest": ("Vitest", "TOOL"),
        }
        for dep, version in self.node_deps.items():
            dl = dep.lower().lstrip("@")
            if dep.lower() in NODE_TECH:
                name, cat = NODE_TECH[dep.lower()]
                add_tech(name, version, 0.99, cat, "package.json")
            elif dl in NODE_TECH:
                name, cat = NODE_TECH[dl]
                add_tech(name, version, 0.99, cat, "package.json")
        if self.node_deps:
            add_tech("Node.js", None, 0.97, "RUNTIME", "package.json")
        if any("typescript" in d.lower() or d.endswith(".ts") or d.endswith(".tsx")
               for d in (list(self.node_deps.keys()) + scan.files)):
            add_tech("TypeScript", None, 0.95, "LANGUAGE", "package.json")

        # From imports (source code)
        IMPORT_TECH = {
            "fastapi": ("FastAPI", "FRAMEWORK", 0.95),
            "flask": ("Flask", "FRAMEWORK", 0.95),
            "django": ("Django", "FRAMEWORK", 0.95),
            "sqlalchemy": ("SQLAlchemy", "DATABASE", 0.93),
            "langchain": ("LangChain", "ML", 0.95),
            "crewai": ("CrewAI", "ML", 0.95),
            "openai": ("OpenAI", "ML", 0.93),
            "ollama": ("Ollama", "ML", 0.92),
            "chromadb": ("ChromaDB", "DATABASE", 0.92),
            "pydantic": ("Pydantic", "FRAMEWORK", 0.92),
            "celery": ("Celery", "TOOL", 0.92),
            "redis": ("Redis", "DATABASE", 0.90),
            "pytest": ("Pytest", "TOOL", 0.88),
        }
        all_imports: Set[str] = set()
        for imps in self.imports.values():
            all_imports.update(imp.lower() for imp in imps)
        for imp, (name, cat, conf) in IMPORT_TECH.items():
            if imp in all_imports:
                add_tech(name, None, conf, cat, "import")

        # From routes
        if self.routes:
            fastapi_routes = [r for r in self.routes if r.framework == "fastapi"]
            if fastapi_routes:
                add_tech("FastAPI", None, 0.97, "FRAMEWORK", "route_decorators")
            express_routes = [r for r in self.routes if r.framework == "express"]
            if express_routes:
                add_tech("Express.js", None, 0.95, "FRAMEWORK", "route_declarations")

        # From file extensions
        exts = {f.rsplit(".", 1)[-1].lower() for f in scan.files if "." in f}
        if "py" in exts:
            add_tech("Python", None, 0.95, "LANGUAGE", "file_extensions")
        if "ts" in exts or "tsx" in exts:
            add_tech("TypeScript", None, 0.90, "LANGUAGE", "file_extensions")
        if "go" in exts:
            add_tech("Go", None, 0.90, "LANGUAGE", "file_extensions")
        if "rs" in exts:
            add_tech("Rust", None, 0.90, "LANGUAGE", "file_extensions")
        if "java" in exts:
            add_tech("Java", None, 0.90, "LANGUAGE", "file_extensions")
        if "cs" in exts:
            add_tech("C#", None, 0.90, "LANGUAGE", "file_extensions")

        # From docker
        if self.docker_images:
            add_tech("Docker", None, 0.97, "TOOL", "dockerfile")
        if self.docker_services:
            add_tech("Docker Compose", None, 0.95, "TOOL", "docker-compose.yml")
        if self.go_deps:
            add_tech("Go", None, 0.99, "LANGUAGE", "go.mod")
        if self.rust_deps:
            add_tech("Rust", None, 0.99, "LANGUAGE", "Cargo.toml")
        if self.java_deps:
            add_tech("Java", None, 0.99, "LANGUAGE", "pom.xml")

        self.technologies = sorted(tech_map.values(), key=lambda t: -t.confidence)

    def _count_aggregate_stats(self) -> None:
        for file_symbols in self.symbols.values():
            self.total_ast_nodes += len(file_symbols)

    # ──────────────────────────────────────────────────────────────────────────
    # Dependency manifest parsers
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_requirements_txt(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-", "http", "git")):
                continue
            for sep in ("==", ">=", "<=", "!=", "~=", ">", "<", "["):
                if sep in line:
                    parts = line.split(sep, 1)
                    deps[parts[0].strip().lower()] = parts[1].split(";")[0].strip() if len(parts) > 1 else ""
                    break
            else:
                deps[line.lower()] = ""
        return deps

    def _parse_pyproject_toml(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        # Look for dependencies = [...] or [tool.poetry.dependencies]
        dep_pattern = re.compile(r'^\s*(?:"|\')?([a-zA-Z0-9_\-\.]+)(?:"|\')??\s*[=:><!].*$', re.MULTILINE)
        in_deps = False
        for line in content.splitlines():
            if "dependencies" in line.lower() and "[" in line:
                in_deps = True
            elif line.strip().startswith("[") and in_deps:
                in_deps = False
            if in_deps:
                m = dep_pattern.match(line)
                if m:
                    name = m.group(1).strip().lower()
                    if name and name not in ("python", "version"):
                        deps[name] = ""
        return deps

    def _parse_pipfile(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        in_packages = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped in ("[packages]", "[dev-packages]"):
                in_packages = True
                continue
            if stripped.startswith("["):
                in_packages = False
            if in_packages and "=" in stripped:
                name = stripped.split("=")[0].strip().strip('"').lower()
                deps[name] = ""
        return deps

    def _parse_package_json(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        try:
            data = json.loads(content)
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                for name, version in (data.get(section) or {}).items():
                    deps[name.lower()] = str(version).lstrip("^~>=<")
        except Exception:
            pass
        return deps

    def _parse_go_mod(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("require ") or (line and not line.startswith(("module", "go ", "//", ")", "(", "replace"))):
                parts = line.split()
                if len(parts) >= 2:
                    deps[parts[0]] = parts[1] if len(parts) > 1 else ""
        return deps

    def _parse_cargo_toml(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped in ("[dependencies]", "[dev-dependencies]", "[build-dependencies]"):
                in_deps = True
                continue
            if stripped.startswith("["):
                in_deps = False
            if in_deps and "=" in stripped and not stripped.startswith("#"):
                name = stripped.split("=")[0].strip().strip('"')
                deps[name.lower()] = ""
        return deps

    def _parse_pom_xml(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        art_pattern = re.compile(r'<artifactId>([^<]+)</artifactId>')
        ver_pattern = re.compile(r'<version>([^<]+)</version>')
        artifacts = art_pattern.findall(content)
        versions = ver_pattern.findall(content)
        for i, art in enumerate(artifacts):
            deps[art.lower()] = versions[i] if i < len(versions) else ""
        return deps

    def _parse_gradle(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        pattern = re.compile(r'(?:implementation|api|compile|testImplementation)["\s].*?["\']([a-zA-Z0-9_.\-]+:[a-zA-Z0-9_.\-]+:[a-zA-Z0-9_.\-]+)["\']')
        for m in pattern.findall(content):
            parts = m.split(":")
            if len(parts) >= 3:
                deps[parts[1].lower()] = parts[2]
        return deps

    def _parse_csproj(self, content: str) -> Dict[str, str]:
        deps: Dict[str, str] = {}
        pattern = re.compile(r'PackageReference Include="([^"]+)"(?:[^/]*?Version="([^"]+)")?')
        for m in pattern.finditer(content):
            deps[m.group(1).lower()] = m.group(2) or ""
        return deps

    def _parse_dockerfile(self, content: str) -> List[str]:
        images = []
        from_re = re.compile(r'^\s*FROM\s+(\S+)', re.IGNORECASE | re.MULTILINE)
        for m in from_re.findall(content):
            if m.lower() not in ("scratch",) and not m.startswith("$"):
                images.append(m)
        return images

    def _parse_docker_compose(self, fpath: str, content: str) -> None:
        try:
            import yaml
            compose = yaml.safe_load(content)
            services = (compose or {}).get("services", {})
            if isinstance(services, dict):
                for sname, sconfig in services.items():
                    self.docker_services.append(sname)
                    img = (sconfig or {}).get("image", "")
                    if img:
                        self.docker_images.append(img)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _name_from_node(node: Any) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            val = SemanticIndex._name_from_node(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return ""

    def get_all_symbols_flat(self) -> List[SymbolRecord]:
        """Return flat list of all SymbolRecords across all files."""
        result = []
        for syms in self.symbols.values():
            result.extend(syms)
        return result

    def get_tech_names(self) -> List[str]:
        """Return list of detected technology names sorted by confidence."""
        return [t.name for t in self.technologies]

    def get_all_deps(self) -> Dict[str, str]:
        """Return merged dependency dict across all ecosystems."""
        merged: Dict[str, str] = {}
        for d in (self.python_deps, self.node_deps, self.go_deps,
                  self.rust_deps, self.java_deps, self.csharp_deps):
            merged.update(d)
        return merged

    def _detect_capabilities(self, scan: RepositoryScan) -> None:
        caps = []
        files_lower = [f.lower() for f in scan.files]
        all_deps = self.get_all_deps()
        all_deps_keys = {k.lower() for k in all_deps.keys()}
        
        # 1. Frontend
        has_fe_deps = any(k in all_deps_keys for k in ("react", "vue", "angular", "next", "vite", "svelte", "jquery", "bootstrap", "tailwindcss"))
        has_fe_files = any(f.endswith((".tsx", ".jsx", ".html", ".css", ".scss")) for f in files_lower)
        if has_fe_deps or has_fe_files:
            caps.append("Frontend")
            
        # 2. Backend
        has_be_deps = any(k in all_deps_keys for k in ("fastapi", "flask", "django", "express", "spring", "rails", "laravel", "uvicorn", "gunicorn", "pydantic"))
        has_be_routes = len(self.routes) > 0
        if has_be_deps or has_be_routes:
            caps.append("Backend")
            
        # 3. Mobile
        has_mobile_deps = any(k in all_deps_keys for k in ("react-native", "flutter", "cordova", "ionic"))
        has_mobile_dirs = any("android/" in f or "ios/" in f for f in files_lower)
        if has_mobile_deps or has_mobile_dirs:
            caps.append("Mobile")
            
        # 4. Desktop
        has_desktop_deps = any(k in all_deps_keys for k in ("electron", "tauri", "pyqt5", "pyqt6", "pyside2", "pyside6"))
        if has_desktop_deps:
            caps.append("Desktop")
            
        # 5. CLI
        has_cli_deps = any(k in all_deps_keys for k in ("click", "typer", "argparse", "commander", "yargs"))
        has_cli_files = any("cli" in f for f in files_lower)
        if has_cli_deps or has_cli_files:
            caps.append("CLI")
            
        # 6. AI
        has_ai_deps = any(k in all_deps_keys for k in ("crewai", "langchain", "autogen", "semantic-kernel", "openai", "anthropic", "chromadb", "faiss-cpu", "faiss-gpu", "litellm"))
        has_agent_files = any("agent" in f or "crew" in f or "chain" in f for f in files_lower)
        if has_ai_deps or has_agent_files:
            caps.append("AI")
            
        # 7. ML
        has_ml_deps = any(k in all_deps_keys for k in ("numpy", "pandas", "scipy", "scikit-learn", "sklearn", "tensorflow", "torch", "pytorch", "keras", "transformers", "xgboost"))
        if has_ml_deps:
            caps.append("ML")
            
        # 8. Infrastructure
        has_infra_files = any(f.endswith((".tf", ".tfvars")) or "terraform" in f or "kubernetes" in f or "helm" in f or "k8s" in f or "ansible" in f for f in files_lower)
        if has_infra_files:
            caps.append("Infrastructure")
            
        # 9. DevOps
        has_devops_files = any(".github/workflows/" in f or ".gitlab-ci" in f or "jenkinsfile" in f or "dockerfile" in f or "docker-compose" in f for f in files_lower)
        if has_devops_files:
            caps.append("DevOps")
            
        # 10. Containerized
        has_docker = any("dockerfile" in f or "docker-compose" in f or "compose.yaml" in f or "compose.yml" in f for f in files_lower) or len(self.docker_images) > 0
        if has_docker:
            caps.append("Containerized")
            
        # 11. Distributed
        has_dist_deps = any(k in all_deps_keys for k in ("pika", "rabbitmq", "kafka", "confluent-kafka", "celery", "redis", "grpcio", "protobuf"))
        if has_dist_deps:
            caps.append("Distributed")
            
        # 12. Microservices
        if len(self.docker_services) > 1 or (has_docker and has_dist_deps):
            caps.append("Microservices")
            
        # 13. Plugin Architecture
        has_plugin_indicator = any("plugin" in f or "extension" in f for f in files_lower)
        if has_plugin_indicator:
            caps.append("Plugin Architecture")
            
        # 14. Event Driven
        has_event_deps = any(k in all_deps_keys for k in ("pika", "kafka", "mqtt", "websockets"))
        has_event_vars = any("event" in f or "emitter" in f or "publish" in f for f in files_lower)
        if has_event_deps or has_event_vars:
            caps.append("Event Driven")
            
        # 15. Serverless
        has_serverless = any("serverless" in f or "lambda" in f or "cloudfunction" in f for f in files_lower)
        if has_serverless:
            caps.append("Serverless")
            
        # 16. Documentation
        has_docs = any("readme" in f or "docs/" in f or f.endswith((".md", ".rst")) for f in files_lower)
        if has_docs:
            caps.append("Documentation")
            
        # 17. Library
        has_setup = any(f in ("setup.py", "setup.cfg", "pyproject.toml", "cargo.toml", "go.mod") for f in scan.files)
        if has_setup and not has_be_routes:
            caps.append("Library")
            
        # 18. Hybrid
        if (("Frontend" in caps and "Backend" in caps) or 
            ("AI" in caps and "Frontend" in caps) or 
            ("Library" in caps and "CLI" in caps)):
            caps.append("Hybrid")
            
        self.capabilities = list(dict.fromkeys(caps))

