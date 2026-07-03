import hashlib
from typing import List, Dict, Any, Optional
from intelligence.models import SymbolRecord, EvidenceRecord
from intelligence.parsers.parser_registry import ParserRegistry

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
    "RULE_SQLALCHEMY_MODEL": {
        "category": "DATABASE",
        "severity": "INFO",
        "description": "SQLAlchemy Declarative Database Schema Model",
        "recommendation_template": "Ensure columns with high search volumes have indexes (index=True) and declare proper relationships.",
        "documentation_reference": "https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html"
    },
    "RULE_DOCKERFILE": {
        "category": "DEPLOYMENT",
        "severity": "LOW",
        "description": "Dockerfile / Container deployment recipe",
        "recommendation_template": "Use multi-stage builds to reduce image size and run containers as non-root users for security.",
        "documentation_reference": "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/"
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
    "RULE_CELERY": {
        "category": "QUEUE",
        "severity": "LOW",
        "description": "Celery Task Queue / Background Job Worker",
        "recommendation_template": "Configure task retries with exponential backoff and monitor task failures with logging.",
        "documentation_reference": "https://docs.celeryq.dev/en/stable/getting-started/introduction.html"
    },
    "RULE_GITHUB_ACTIONS": {
        "category": "CI_CD",
        "severity": "LOW",
        "description": "GitHub Actions Workflow deployment/test pipeline",
        "recommendation_template": "Pin GitHub Actions dependencies to specific commit hashes and limit token permissions to read-only.",
        "documentation_reference": "https://docs.github.com/en/actions"
    }
}

class EvidenceEngine:
    def __init__(self):
        self.evidence: List[EvidenceRecord] = []

    def analyze_repository(
        self,
        symbols: List[SymbolRecord],
        dependencies: Dict[str, str], # Manifest dependencies (e.g. {"fastapi": "0.100.0"})
        security_findings: List[Dict[str, Any]],
        file_imports: Dict[str, List[str]] # Mapping of file -> list of imports
    ) -> List[EvidenceRecord]:
        """Runs the rule engine on parsed repository data to extract evidence."""
        self.evidence = []

        # 1. Map Security Findings into Evidence
        for finding in security_findings:
            rule_id = finding["rule_id"]
            code_snippet = f"{finding.get('description', '')}"
            code_hash = hashlib.sha256(code_snippet.encode("utf-8")).hexdigest()[:16]
            self.evidence.append(EvidenceRecord(
                rule_id=rule_id,
                parser="SecurityEngine",
                language="Python/JS/Regex",
                symbol_name=finding.get("api"),
                file_path=finding["file_path"],
                line_start=finding["line_start"],
                line_end=finding["line_end"],
                column_start=finding["column_start"],
                column_end=finding["column_end"],
                matched_code_hash=code_hash,
                confidence=finding["confidence"],
                severity=finding["severity"]
            ))

        # 2. Check imports and symbols for rules
        # Let's group symbols by file for lookup
        by_file: Dict[str, List[SymbolRecord]] = {}
        for sym in symbols:
            if sym.file_path not in by_file:
                by_file[sym.file_path] = []
            by_file[sym.file_path].append(sym)

        for file_path, file_symbols in by_file.items():
            ext = file_path.split(".")[-1].lower() if "." in file_path else "unknown"
            imports = file_imports.get(file_path, [])
            
            # RULE_FASTAPI_ROUTER
            has_router_symbol = any(s.type == "route" for s in file_symbols)
            has_fastapi_import = any("fastapi" in imp.lower() for imp in imports)
            if has_router_symbol or has_fastapi_import:
                confidence = 0.55
                if has_router_symbol and has_fastapi_import:
                    confidence = 0.95
                if "fastapi" in dependencies:
                    confidence = 0.99
                
                # Pick one representative route/symbol for highlighting
                rep_sym = next((s for s in file_symbols if s.type == "route"), file_symbols[0])
                code_hash = hashlib.sha256(rep_sym.name.encode()).hexdigest()[:16]
                
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_FASTAPI_ROUTER",
                    parser=f"{ext.upper()}Parser",
                    language=ext,
                    symbol_name=rep_sym.name,
                    file_path=file_path,
                    line_start=rep_sym.line_start,
                    line_end=rep_sym.line_end,
                    column_start=rep_sym.column_start,
                    column_end=rep_sym.column_end,
                    matched_code_hash=code_hash,
                    confidence=confidence,
                    severity="INFO"
                ))

            # RULE_SQLALCHEMY_MODEL
            db_models = [s for s in file_symbols if s.type == "model"]
            has_db_imports = any(any(db_term in imp.lower() for db_term in ("sqlalchemy", "declarative", "orm")) for imp in imports)
            if db_models or has_db_imports:
                confidence = 0.55
                if db_models and has_db_imports:
                    confidence = 0.95
                if "sqlalchemy" in dependencies:
                    confidence = 0.99
                
                rep_sym = db_models[0] if db_models else file_symbols[0]
                code_hash = hashlib.sha256(rep_sym.name.encode()).hexdigest()[:16]

                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_SQLALCHEMY_MODEL",
                    parser=f"{ext.upper()}Parser",
                    language=ext,
                    symbol_name=rep_sym.name,
                    file_path=file_path,
                    line_start=rep_sym.line_start,
                    line_end=rep_sym.line_end,
                    column_start=rep_sym.column_start,
                    column_end=rep_sym.column_end,
                    matched_code_hash=code_hash,
                    confidence=confidence,
                    severity="INFO"
                ))

            # RULE_AUTH_JWT
            has_jwt_import = any("jwt" in imp.lower() for imp in imports)
            if has_jwt_import:
                confidence = 0.90
                if "pyjwt" in dependencies or "jsonwebtoken" in dependencies:
                    confidence = 0.99
                
                rep_sym = file_symbols[0] if file_symbols else None
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_AUTH_JWT",
                    parser=f"{ext.upper()}Parser",
                    language=ext,
                    symbol_name=rep_sym.name if rep_sym else "jwt",
                    file_path=file_path,
                    line_start=rep_sym.line_start if rep_sym else 1,
                    line_end=rep_sym.line_end if rep_sym else 1,
                    column_start=rep_sym.column_start if rep_sym else 0,
                    column_end=rep_sym.column_end if rep_sym else 0,
                    matched_code_hash=hashlib.sha256(b"jwt").hexdigest()[:16],
                    confidence=confidence,
                    severity="MEDIUM"
                ))

            # RULE_VECTOR_DB
            vdb_terms = ("chroma", "pinecone", "faiss", "milvus")
            has_vdb_import = any(any(term in imp.lower() for term in vdb_terms) for imp in imports)
            if has_vdb_import:
                matched_vdb = next(term for term in vdb_terms if any(term in imp.lower() for imp in imports))
                confidence = 0.90
                if matched_vdb in dependencies:
                    confidence = 0.99

                rep_sym = file_symbols[0] if file_symbols else None
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_VECTOR_DB",
                    parser=f"{ext.upper()}Parser",
                    language=ext,
                    symbol_name=rep_sym.name if rep_sym else matched_vdb,
                    file_path=file_path,
                    line_start=rep_sym.line_start if rep_sym else 1,
                    line_end=rep_sym.line_end if rep_sym else 1,
                    column_start=rep_sym.column_start if rep_sym else 0,
                    column_end=rep_sym.column_end if rep_sym else 0,
                    matched_code_hash=hashlib.sha256(matched_vdb.encode()).hexdigest()[:16],
                    confidence=confidence,
                    severity="LOW"
                ))

            # RULE_OLLAMA
            has_ollama_import = any("ollama" in imp.lower() for imp in imports)
            if has_ollama_import:
                confidence = 0.90
                if "ollama" in dependencies:
                    confidence = 0.99
                
                rep_sym = file_symbols[0] if file_symbols else None
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_OLLAMA",
                    parser=f"{ext.upper()}Parser",
                    language=ext,
                    symbol_name=rep_sym.name if rep_sym else "ollama",
                    file_path=file_path,
                    line_start=rep_sym.line_start if rep_sym else 1,
                    line_end=rep_sym.line_end if rep_sym else 1,
                    column_start=rep_sym.column_start if rep_sym else 0,
                    column_end=rep_sym.column_end if rep_sym else 0,
                    matched_code_hash=hashlib.sha256(b"ollama").hexdigest()[:16],
                    confidence=confidence,
                    severity="LOW"
                ))

            # RULE_LANGCHAIN
            has_lc_import = any("langchain" in imp.lower() for imp in imports)
            if has_lc_import:
                confidence = 0.90
                if "langchain" in dependencies:
                    confidence = 0.99

                rep_sym = file_symbols[0] if file_symbols else None
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_LANGCHAIN",
                    parser=f"{ext.upper()}Parser",
                    language=ext,
                    symbol_name=rep_sym.name if rep_sym else "langchain",
                    file_path=file_path,
                    line_start=rep_sym.line_start if rep_sym else 1,
                    line_end=rep_sym.line_end if rep_sym else 1,
                    column_start=rep_sym.column_start if rep_sym else 0,
                    column_end=rep_sym.column_end if rep_sym else 0,
                    matched_code_hash=hashlib.sha256(b"langchain").hexdigest()[:16],
                    confidence=confidence,
                    severity="LOW"
                ))

            # RULE_CELERY
            has_celery_import = any("celery" in imp.lower() for imp in imports)
            if has_celery_import:
                confidence = 0.90
                if "celery" in dependencies:
                    confidence = 0.99

                rep_sym = file_symbols[0] if file_symbols else None
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_CELERY",
                    parser=f"{ext.upper()}Parser",
                    language=ext,
                    symbol_name=rep_sym.name if rep_sym else "celery",
                    file_path=file_path,
                    line_start=rep_sym.line_start if rep_sym else 1,
                    line_end=rep_sym.line_end if rep_sym else 1,
                    column_start=rep_sym.column_start if rep_sym else 0,
                    column_end=rep_sym.column_end if rep_sym else 0,
                    matched_code_hash=hashlib.sha256(b"celery").hexdigest()[:16],
                    confidence=confidence,
                    severity="LOW"
                ))

        # 3. Add file-level configuration rule matches
        for file_path in file_imports.keys():
            ext = file_path.split(".")[-1].lower() if "." in file_path else "unknown"
            name = file_path.split("/")[-1].lower()
            
            # RULE_DOCKERFILE
            if "dockerfile" in name or name == "docker-compose.yml":
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_DOCKERFILE",
                    parser="UnknownParser",
                    language=ext,
                    symbol_name=name,
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    column_start=0,
                    column_end=0,
                    matched_code_hash=hashlib.sha256(name.encode()).hexdigest()[:16],
                    confidence=0.99,
                    severity="LOW"
                ))

            # RULE_GITHUB_ACTIONS
            if ".github/workflows/" in file_path:
                self.evidence.append(EvidenceRecord(
                    rule_id="RULE_GITHUB_ACTIONS",
                    parser="UnknownParser",
                    language="yaml",
                    symbol_name=name,
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    column_start=0,
                    column_end=0,
                    matched_code_hash=hashlib.sha256(name.encode()).hexdigest()[:16],
                    confidence=0.99,
                    severity="LOW"
                ))

        return self.evidence
