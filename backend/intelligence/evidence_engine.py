"""
evidence_engine.py — Rule engine extracting static analysis evidence from SemanticIndex.

Consumes SemanticIndex (shared index from single scan pass) to populate EvidenceRecords.
Avoids redundant scans or regex matching on raw files.
"""
from __future__ import annotations

import hashlib
import logging
from typing import List, Dict, Any, Optional

from intelligence.models import SymbolRecord, EvidenceRecord
from intelligence.semantic_index import SemanticIndex

logger = logging.getLogger(__name__)

# Defined Rules metadata
RULES_METADATA = {
    "RULE_AUTH_JWT": {
        "category": "AUTHENTICATION",
        "severity": "MEDIUM",
        "description": "JSON Web Token (JWT) based authentication",
        "recommendation_template": "Ensure JWT secrets are stored in environment variables and tokens have appropriate expiration (exp) claims.",
        "documentation_reference": "https://jwt.io/introduction/"
    },
    "RULE_FASTAPI_ROUTER": {
        "category": "REST_API",
        "severity": "INFO",
        "description": "FastAPI Web Router route handlers",
        "recommendation_template": "Group FastAPI routers cleanly in an api/ or routes/ module and use dependency injection for database sessions.",
        "documentation_reference": "https://fastapi.tiangolo.com/tutorial/bigger-applications/"
    },
    "RULE_FASTAPI_ENDPOINT": {
        "category": "REST_API",
        "severity": "INFO",
        "description": "FastAPI Route Endpoint Handler",
        "recommendation_template": "Structure API endpoints with explicit request/response schemas and validate input models.",
        "documentation_reference": "https://fastapi.tiangolo.com/tutorial/body/"
    },
    "RULE_SQLALCHEMY_MODEL": {
        "category": "DATABASE",
        "severity": "INFO",
        "description": "SQLAlchemy Declarative Database Schema Model",
        "recommendation_template": "Ensure columns with high search volumes have indexes (index=True) and declare proper relationships.",
        "documentation_reference": "https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html"
    },
    "RULE_PYDANTIC_MODEL": {
        "category": "MODELS",
        "severity": "INFO",
        "description": "Pydantic Data validation Schema Model",
        "recommendation_template": "Use Pydantic schemas for request/response serialization to ensure strict runtime type safety.",
        "documentation_reference": "https://docs.pydantic.dev/"
    },
    "RULE_ORM_QUERY": {
        "category": "DATABASE",
        "severity": "INFO",
        "description": "ORM query pattern detected",
        "recommendation_template": "Leverage select() statements with session.execute() instead of session.query() for SQLAlchemy 2.0 compatibility.",
        "documentation_reference": "https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html"
    },
    "RULE_DOCKERFILE": {
        "category": "DEPLOYMENT",
        "severity": "LOW",
        "description": "Dockerfile / Container deployment recipe",
        "recommendation_template": "Use multi-stage builds to reduce image size and run containers as non-root users for security.",
        "documentation_reference": "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/"
    },
    "RULE_DOCKER_MULTI_SERVICE": {
        "category": "DEPLOYMENT",
        "severity": "LOW",
        "description": "Docker Compose Multi-Container Orchestration",
        "recommendation_template": "Use compose depends_on rules to control container startup orders and check service healthiness.",
        "documentation_reference": "https://docs.docker.com/compose/"
    },
    "RULE_VECTOR_DB": {
        "category": "VECTOR_DATABASE",
        "severity": "LOW",
        "description": "Vector Database Client Integration (Chroma / Pinecone / FAISS / Milvus)",
        "recommendation_template": "Initialize vector DB clients as singletons and reuse connections across queries to prevent socket leaks.",
        "documentation_reference": "https://docs.trychroma.com/"
    },
    "RULE_OLLAMA": {
        "category": "ML",
        "severity": "LOW",
        "description": "Ollama LLM local inference client",
        "recommendation_template": "Add proper timeout configurations and fallback exception handling for local LLM requests.",
        "documentation_reference": "https://github.com/ollama/ollama"
    },
    "RULE_LANGCHAIN": {
        "category": "ML",
        "severity": "LOW",
        "description": "LangChain LLM orchestration framework",
        "recommendation_template": "Pin LangChain package versions and separate prompt templates from application logic.",
        "documentation_reference": "https://python.langchain.com/docs/get_started/introduction"
    },
    "RULE_CREWAI": {
        "category": "ML",
        "severity": "LOW",
        "description": "CrewAI Multi-Agent Coordination Framework",
        "recommendation_template": "Configure agent memory options and use clean LLM integration hooks to keep agents deterministic.",
        "documentation_reference": "https://docs.crewai.com/"
    },
    "RULE_CREWAI_AGENT": {
        "category": "ML",
        "severity": "LOW",
        "description": "CrewAI Autonomous Agent definition",
        "recommendation_template": "Define custom agent tools and verify prompt templates to guide agent task executions.",
        "documentation_reference": "https://docs.crewai.com/concepts/agents/"
    },
    "RULE_CELERY": {
        "category": "QUEUE",
        "severity": "LOW",
        "description": "Celery Task Queue / Background Job Worker",
        "recommendation_template": "Configure task retries with exponential backoff and monitor task failures with logging.",
        "documentation_reference": "https://docs.celeryq.dev/en/stable/getting-started/introduction.html"
    },
    "RULE_BACKGROUND_TASK": {
        "category": "QUEUE",
        "severity": "LOW",
        "description": "Concurrent Background Execution worker",
        "recommendation_template": "Avoid running raw threads; use managed task queues or fastapi BackgroundTasks instead.",
        "documentation_reference": "https://fastapi.tiangolo.com/tutorial/background-tasks/"
    },
    "RULE_GITHUB_ACTIONS": {
        "category": "CI_CD",
        "severity": "LOW",
        "description": "GitHub Actions Workflow deployment/test pipeline",
        "recommendation_template": "Pin GitHub Actions dependencies to specific commit hashes and limit token permissions to read-only.",
        "documentation_reference": "https://docs.github.com/en/actions"
    },
    "RULE_REACT": {
        "category": "FRONTEND",
        "severity": "INFO",
        "description": "React.js Client Framework Integration",
        "recommendation_template": "Structure UI components under a components/ directory and manage state hooks predictably.",
        "documentation_reference": "https://react.dev/"
    },
    "RULE_TYPESCRIPT_CODE": {
        "category": "LANGUAGES",
        "severity": "INFO",
        "description": "TypeScript Static Typing Definition File",
        "recommendation_template": "Enforce strict type checking in tsconfig.json and avoid using the 'any' type.",
        "documentation_reference": "https://www.typescriptlang.org/docs/"
    },
    "RULE_JAVASCRIPT_CODE": {
        "category": "LANGUAGES",
        "severity": "INFO",
        "description": "JavaScript Application Source File",
        "recommendation_template": "Consider migrating critical modules to TypeScript for enhanced compiler-level type safety.",
        "documentation_reference": "https://developer.mozilla.org/en-US/docs/Web/JavaScript"
    },
    "RULE_PYTHON_CODE": {
        "category": "LANGUAGES",
        "severity": "INFO",
        "description": "Python Backend Application Source File",
        "recommendation_template": "Adhere to PEP 8 style guidelines and include function docstrings and type hints.",
        "documentation_reference": "https://peps.python.org/pep-0008/"
    },
    "RULE_SQLITE": {
        "category": "DATABASE",
        "severity": "INFO",
        "description": "SQLite Local Embedded Database Storage",
        "recommendation_template": "Use WAL mode for SQLite when executing concurrent reads and writes to prevent locking issues.",
        "documentation_reference": "https://sqlite.org/wal.html"
    },
    "RULE_POSTGRESQL": {
        "category": "DATABASE",
        "severity": "INFO",
        "description": "PostgreSQL Production Relational Database Store",
        "recommendation_template": "Implement database connection pooling (e.g. pg_bouncer) to scale connection workloads.",
        "documentation_reference": "https://www.postgresql.org/docs/"
    },
    "RULE_TAILWIND": {
        "category": "FRONTEND",
        "severity": "INFO",
        "description": "Tailwind Utility-First CSS Framework Configurations",
        "recommendation_template": "Keep tailwind configs customized and purge unused styles in production configurations.",
        "documentation_reference": "https://tailwindcss.com/docs"
    },
    "RULE_PYTEST": {
        "category": "TESTING",
        "severity": "INFO",
        "description": "Pytest Test Suite Integration",
        "recommendation_template": "Structure tests cleanly under a tests/ folder and write fixtures to share test setup code.",
        "documentation_reference": "https://docs.pytest.org/"
    },
    "RULE_JEST": {
        "category": "TESTING",
        "severity": "INFO",
        "description": "Jest Front-end JavaScript Testing Suite",
        "recommendation_template": "Mock external API modules and use react-testing-library to test user interaction flows.",
        "documentation_reference": "https://jestjs.io/"
    },
    "RULE_ENV_VAR_USAGE": {
        "category": "CONFIGURATION",
        "severity": "INFO",
        "description": "Environment variable retrieval configuration",
        "recommendation_template": "Centralize all env var access in a settings configuration file and validate with Pydantic.",
        "documentation_reference": "https://docs.pydantic.dev/latest/concepts/pydantic_settings/"
    },
    "RULE_ASYNC_API": {
        "category": "REST_API",
        "severity": "INFO",
        "description": "Asynchronous API endpoint definition",
        "recommendation_template": "Ensure thread-safety when invoking synchronous DB operations inside async FastAPI routes.",
        "documentation_reference": "https://fastapi.tiangolo.com/async/"
    },
}


class EvidenceEngine:
    def __init__(self):
        self.evidence: List[EvidenceRecord] = []

    def analyze_repository(
        self,
        symbols: List[SymbolRecord],
        dependencies: Any,
        security_findings: List[Dict[str, Any]],
        file_imports: Dict[str, List[str]],
        all_files: Optional[List[str]] = None,
        semantic_index: Optional[SemanticIndex] = None,
    ) -> List[EvidenceRecord]:
        """
        Runs the rule engine on parsed repository data to extract evidence.
        Uses SemanticIndex as primary data source if provided.
        """
        from intelligence.utils import safe_list, safe_dict, normalize_dependency_name, normalize_path
        import hashlib

        self.evidence = []

        # ── 1. Map Security Findings into Evidence ────────────────────────────
        for finding in safe_list(security_findings):
            rule_id = finding.get("rule_id") or "RULE_SECURITY_ISSUE"
            code_snippet = f"{finding.get('description', '')}"
            code_hash = hashlib.sha256(code_snippet.encode("utf-8")).hexdigest()[:16]
            self.evidence.append(EvidenceRecord(
                rule_id=rule_id,
                parser="SecurityEngine",
                language="Python/JS/Regex",
                symbol_name=finding.get("api"),
                file_path=normalize_path(finding["file_path"]),
                line_start=finding.get("line_start") or 1,
                line_end=finding.get("line_end") or 1,
                column_start=finding.get("column_start") or 0,
                column_end=finding.get("column_end") or 0,
                matched_code_hash=code_hash,
                confidence=finding.get("confidence") or 0.8,
                severity=finding.get("severity") or "INFO"
            ))

        # ── 2. Run AST/Dependency rules using SemanticIndex ───────────────────
        if semantic_index is not None:
            self._run_semantic_index_rules(semantic_index)
            return self.evidence

        # ── 3. Fallback path (compatibility for old callers) ─────────────────
        symbols = safe_list(symbols)
        file_imports = safe_dict(file_imports)
        if all_files is None:
            all_files = list(file_imports.keys())
        all_files = [normalize_path(f) for f in all_files]

        dep_names = set()
        for dep in safe_list(dependencies):
            name = normalize_dependency_name(dep)
            if name:
                dep_names.add(name)

        by_file: Dict[str, List[SymbolRecord]] = {}
        for sym in symbols:
            fpath = normalize_path(sym.file_path)
            if fpath not in by_file:
                by_file[fpath] = []
            by_file[fpath].append(sym)

        for file_path, file_symbols in by_file.items():
            ext = file_path.split(".")[-1].lower() if "." in file_path else "unknown"
            imports = file_imports.get(file_path, [])
            dep_names_lower = {d.lower() for d in dep_names}

            # RULE_FASTAPI_ROUTER
            has_router_symbol = any(s.type == "route" for s in file_symbols)
            has_fastapi_import = any("fastapi" in imp.lower() for imp in imports)
            if has_router_symbol or has_fastapi_import:
                confidence = 0.95
                if "fastapi" in dep_names_lower:
                    confidence = 0.99
                rep_sym = next((s for s in file_symbols if s.type == "route"), file_symbols[0])
                code_hash = hashlib.sha256(rep_sym.name.encode()).hexdigest()[:16]
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_FASTAPI_ROUTER", parser=f"{ext.upper()}Parser", language=ext,
                    symbol_name=rep_sym.name, file_path=file_path,
                    line_start=rep_sym.line_start, line_end=rep_sym.line_end,
                    column_start=rep_sym.column_start, column_end=rep_sym.column_end,
                    matched_code_hash=code_hash, confidence=confidence, severity="INFO"
                ))

            # RULE_SQLALCHEMY_MODEL
            db_models = [s for s in file_symbols if s.type == "model"]
            has_db_imports = any(any(db_term in imp.lower() for db_term in ("sqlalchemy", "declarative", "orm")) for imp in imports)
            if db_models or has_db_imports:
                confidence = 0.95
                if "sqlalchemy" in dep_names_lower:
                    confidence = 0.99
                rep_sym = db_models[0] if db_models else file_symbols[0]
                code_hash = hashlib.sha256(rep_sym.name.encode()).hexdigest()[:16]
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_SQLALCHEMY_MODEL", parser=f"{ext.upper()}Parser", language=ext,
                    symbol_name=rep_sym.name, file_path=file_path,
                    line_start=rep_sym.line_start, line_end=rep_sym.line_end,
                    column_start=rep_sym.column_start, column_end=rep_sym.column_end,
                    matched_code_hash=code_hash, confidence=confidence, severity="INFO"
                ))

            # RULE_AUTH_JWT
            has_jwt_import = any("jwt" in imp.lower() for imp in imports)
            if has_jwt_import:
                confidence = 0.90
                if "pyjwt" in dep_names_lower or "jsonwebtoken" in dep_names_lower:
                    confidence = 0.99
                rep_sym = file_symbols[0] if file_symbols else None
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_AUTH_JWT", parser=f"{ext.upper()}Parser", language=ext,
                    symbol_name=rep_sym.name if rep_sym else "jwt", file_path=file_path,
                    line_start=rep_sym.line_start if rep_sym else 1, line_end=rep_sym.line_end if rep_sym else 1,
                    column_start=rep_sym.column_start if rep_sym else 0, column_end=rep_sym.column_end if rep_sym else 0,
                    matched_code_hash=hashlib.sha256(b"jwt").hexdigest()[:16], confidence=confidence, severity="MEDIUM"
                ))

            # RULE_VECTOR_DB
            vdb_terms = ("chroma", "pinecone", "faiss", "milvus")
            has_vdb_import = any(any(term in imp.lower() for term in vdb_terms) for imp in imports)
            if has_vdb_import:
                matched_vdb = next(term for term in vdb_terms if any(term in imp.lower() for imp in imports))
                confidence = 0.90
                if matched_vdb in dep_names_lower:
                    confidence = 0.99
                rep_sym = file_symbols[0] if file_symbols else None
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_VECTOR_DB", parser=f"{ext.upper()}Parser", language=ext,
                    symbol_name=rep_sym.name if rep_sym else matched_vdb, file_path=file_path,
                    line_start=rep_sym.line_start if rep_sym else 1, line_end=rep_sym.line_end if rep_sym else 1,
                    column_start=rep_sym.column_start if rep_sym else 0, column_end=rep_sym.column_end if rep_sym else 0,
                    matched_code_hash=hashlib.sha256(matched_vdb.encode()).hexdigest()[:16], confidence=confidence, severity="LOW"
                ))

        # Path-based broad heuristics fallback
        for file_path in all_files:
            ext = file_path.split(".")[-1].lower() if "." in file_path else "unknown"
            name = file_path.split("/")[-1].lower()
            code_hash = hashlib.sha256(name.encode()).hexdigest()[:16]

            if "dockerfile" in name or name in ("docker-compose.yml", "docker-compose.yaml"):
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_DOCKERFILE", parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.99, severity="LOW"
                ))

            if ".github/workflows/" in file_path:
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_GITHUB_ACTIONS", parser="PathParser", language="yaml",
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.99, severity="LOW"
                ))

            if "react" in name or ext in ("jsx", "tsx") or "frontend/src" in file_path:
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_REACT", parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.90, severity="INFO"
                ))
                if ext in ("ts", "tsx"):
                    self.evidence.append(EvidenceRecord(
                        rule_id="RULE_TYPESCRIPT_CODE", parser="PathParser", language=ext,
                        symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                        column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.95, severity="INFO"
                    ))

            if ext == "js" and "frontend/src" in file_path:
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_JAVASCRIPT_CODE", parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.95, severity="INFO"
                ))

            if "/tests/" in file_path or "/test/" in file_path or "test_" in name or "_test" in name or ".test." in name:
                rule_name = "RULE_JEST" if ext in ("js", "jsx", "ts", "tsx") else "RULE_PYTEST"
                self.evidence.append(EvidenceRecord(
                    rule_id=rule_name, parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.95, severity="INFO"
                ))

            if ext == "py" and not name.startswith("test_"):
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_PYTHON_CODE", parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.95, severity="INFO"
                ))

            if "sqlite" in name or ext == "db" or ext == "sqlite":
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_SQLITE", parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.95, severity="INFO"
                ))

            if "postgres" in name or "postgresql" in name or "psycopg2" in name:
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_POSTGRESQL", parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.95, severity="INFO"
                ))

            if "tailwind" in name:
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_TAILWIND", parser="PathParser", language=ext,
                    symbol_name=name, file_path=file_path, line_start=1, line_end=1,
                    column_start=0, column_end=0, matched_code_hash=code_hash, confidence=0.99, severity="INFO"
                ))

        return self.evidence

    def _run_semantic_index_rules(self, idx: SemanticIndex) -> None:
        """Runs rule logic driven directly by SemanticIndex properties."""

        def add_ev(rule_id: str, fpath: str, sym_name: str, line: int, conf: float, sev: str,
                   source_str: str) -> None:
            h = hashlib.sha256(source_str.encode()).hexdigest()[:16]
            ext = fpath.split(".")[-1].lower() if "." in fpath else "unknown"
            self.evidence.append(EvidenceRecord(
                rule_id=rule_id,
                parser=f"{ext.upper()}Parser" if ext != "unknown" else "SemanticIndexParser",
                language=ext,
                symbol_name=sym_name,
                file_path=fpath,
                line_start=line,
                line_end=line,
                column_start=0,
                column_end=0,
                matched_code_hash=h,
                confidence=conf,
                severity=sev
            ))

        # ── 1. Routes (FastAPI Route Endpoints) ───────────────────────────────
        for route in idx.routes:
            rule = "RULE_FASTAPI_ENDPOINT" if route.framework == "fastapi" else "RULE_FASTAPI_ROUTER"
            add_ev(
                rule, route.file_path, route.function_name, route.line_start,
                0.97, "INFO", f"{route.method}:{route.path or ''}"
            )

        # ── 2. Models (ORM & Pydantic) ────────────────────────────────────────
        for model in idx.models:
            rule = "RULE_PYDANTIC_MODEL" if model.model_type == "pydantic" else "RULE_SQLALCHEMY_MODEL"
            add_ev(
                rule, model.file_path, model.name, model.line_start,
                0.95, "INFO", model.name
            )

        # ── 3. AI Agents (CrewAI / LangChain) ─────────────────────────────────
        for svc in idx.agents_and_services:
            if svc.service_type == "agent":
                add_ev(
                    "RULE_CREWAI_AGENT", svc.file_path, svc.name, svc.line_start,
                    0.95, "LOW", svc.name
                )
            elif svc.service_type == "service":
                # Regular backend business service
                pass

        # ── 4. Env var usages ─────────────────────────────────────────────────
        for var, fpath in idx.env_vars.items():
            add_ev(
                "RULE_ENV_VAR_USAGE", fpath, var, 1,
                0.90, "INFO", var
            )

        # ── 5. Docker Compose multi services ──────────────────────────────────
        if idx.docker_services:
            # Select docker-compose file if in config files
            comp_file = next((f for f in idx.config_files if "docker-compose" in f), "docker-compose.yml")
            add_ev(
                "RULE_DOCKER_MULTI_SERVICE", comp_file, "docker-compose", 1,
                0.95, "LOW", ",".join(idx.docker_services)
            )

        # ── 6. External technologies with imports ─────────────────────────────
        # Scan imports in each file to verify frameworks
        for fpath, imports in idx.imports.items():
            ext = fpath.split(".")[-1].lower() if "." in fpath else ""
            imports_lower = {imp.lower() for imp in imports}

            if "jwt" in imports_lower:
                add_ev("RULE_AUTH_JWT", fpath, "jwt", 1, 0.90, "MEDIUM", "jwt_import")
            if "ollama" in imports_lower:
                add_ev("RULE_OLLAMA", fpath, "ollama", 1, 0.92, "LOW", "ollama_import")
            if "langchain" in imports_lower:
                add_ev("RULE_LANGCHAIN", fpath, "langchain", 1, 0.95, "LOW", "langchain_import")
            if "crewai" in imports_lower:
                add_ev("RULE_CREWAI", fpath, "crewai", 1, 0.95, "LOW", "crewai_import")
            if any(term in imports_lower for term in ("chroma", "pinecone", "faiss")):
                add_ev("RULE_VECTOR_DB", fpath, "vector_db", 1, 0.92, "LOW", "vector_import")
            if "celery" in imports_lower:
                add_ev("RULE_CELERY", fpath, "celery", 1, 0.92, "LOW", "celery_import")

        # ── 7. Fallback file types and names (Broad languages & configs) ──────
        # Ensure we always represent the file languages and standard tools
        for t in idx.technologies:
            tl = t.name.lower()
            # Find a representative file to link this tech evidence to
            rep_file = next((f for f in idx.imports.keys() if f.endswith(f".{tl[:2]}")), None)
            if not rep_file and idx.imports:
                rep_file = next(iter(idx.imports.keys()))
            if not rep_file:
                rep_file = "repository_root"

            if tl == "docker":
                add_ev("RULE_DOCKERFILE", rep_file, "Dockerfile", 1, t.confidence, "LOW", "docker")
            elif tl == "github actions":
                add_ev("RULE_GITHUB_ACTIONS", rep_file, "github-actions", 1, t.confidence, "LOW", "github_actions")
            elif tl == "react":
                add_ev("RULE_REACT", rep_file, "react", 1, t.confidence, "INFO", "react")
            elif tl == "typescript":
                add_ev("RULE_TYPESCRIPT_CODE", rep_file, "typescript", 1, t.confidence, "INFO", "typescript")
            elif tl == "javascript":
                add_ev("RULE_JAVASCRIPT_CODE", rep_file, "javascript", 1, t.confidence, "INFO", "javascript")
            elif tl == "python":
                add_ev("RULE_PYTHON_CODE", rep_file, "python", 1, t.confidence, "INFO", "python")
            elif tl == "sqlite":
                add_ev("RULE_SQLITE", rep_file, "sqlite", 1, t.confidence, "INFO", "sqlite")
            elif tl == "postgresql":
                add_ev("RULE_POSTGRESQL", rep_file, "postgresql", 1, t.confidence, "INFO", "postgresql")
            elif tl == "tailwind css":
                add_ev("RULE_TAILWIND", rep_file, "tailwind", 1, t.confidence, "INFO", "tailwind")
            elif tl == "pytest":
                add_ev("RULE_PYTEST", rep_file, "pytest", 1, t.confidence, "INFO", "pytest")
            elif tl == "jest":
                add_ev("RULE_JEST", rep_file, "jest", 1, t.confidence, "INFO", "jest")
