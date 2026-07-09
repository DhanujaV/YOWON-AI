"""
architecture_engine.py — AST-driven architecture layer detection.

Architecture derives primarily from SemanticIndex (routes, models, agents, services)
extracted during the single-pass repository scan. Evidence rules and path heuristics
serve as supplementary signals only.

16 architecture layers are defined. Non-empty layers produce graph nodes.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, TYPE_CHECKING

from intelligence.models import EvidenceRecord

if TYPE_CHECKING:
    from intelligence.semantic_index import SemanticIndex

# ──────────────────────────────────────────────────────────────────────────────
# Layer definitions (id, label, description)
# ──────────────────────────────────────────────────────────────────────────────

_LAYER_DEFS = [
    ("presentation",       "Presentation",        "Client-facing UI components, layouts, and web templates"),
    ("api",                "API",                 "REST/GraphQL endpoints, API routes, and gateways"),
    ("controllers",        "Controllers",         "Request coordinators, route controllers, and input handlers"),
    ("services",           "Services",            "Core business logic modules and external API wrappers"),
    ("repositories",       "Repositories",        "Data access abstraction interfaces and CRUD layers"),
    ("models",             "Models",              "ORM models, database schemas, and Pydantic validators"),
    ("database",           "Database",            "Raw SQL connectors, migrations, and database scripts"),
    ("authentication",     "Authentication",      "User identity verification, JWT tokens, and OAuth"),
    ("authorization",      "Authorization",       "RBAC, permissions logic, and access control"),
    ("caching",            "Caching",             "Redis, Memcached, and local cache layers"),
    ("workers",            "Workers",             "Async task queue workers and thread pool jobs"),
    ("schedulers",         "Schedulers",          "Cron triggers, background intervals, and periodic jobs"),
    ("configuration",      "Configuration",       "Settings files, environment parsers, and constants"),
    ("testing",            "Testing",             "Unit, integration, and end-to-end test suites"),
    ("monitoring",         "Monitoring",          "Observability, Prometheus metrics, and OpenTelemetry logging"),
    ("ai_agents",          "AI Agents",           "CrewAI agents, LangChain chains, and agent orchestrators"),
    ("prompt_manager",     "Prompt Manager",      "Prompt templates, system messages, and formatting tools"),
    ("memory",             "Memory",              "Vector databases, semantic caches, and conversational history"),
    ("planner",            "Planner",             "Reasoning planning engines, ReAct executors, and step routers"),
    ("retriever",          "Retriever",           "RAG pipeline retrievers and search tooling"),
    ("sandbox",            "Sandbox",             "Isolated container runners and virtualenvs"),
    ("runtime",            "Runtime",             "Gunicorn, Uvicorn, node runners, and interpreter setup"),
    ("plugin_system",      "Plugin System",       "Dynamic extensions, load-time hooks, and dynamic imports"),
    ("llm_providers",      "LLM Providers",       "Ollama, OpenAI, Anthropic connectors, and LiteLLM"),
    ("infrastructure",     "Infrastructure",      "Terraform files, Ansible scripts, and Kubernetes YAMLs"),
    ("deployment",         "Deployment",          "Dockerfiles, docker-compose configs, and CI/CD pipelines"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Layer classification rules
# ──────────────────────────────────────────────────────────────────────────────

# Evidence rule_id → layer key
_EVIDENCE_LAYER_MAP: Dict[str, str] = {
    "RULE_REACT":              "presentation",
    "RULE_TAILWIND":           "presentation",
    "RULE_TYPESCRIPT_CODE":    "presentation",
    "RULE_JAVASCRIPT_CODE":    "presentation",
    "RULE_FASTAPI":            "runtime",
    "RULE_FASTAPI_ROUTER":     "api",
    "RULE_FASTAPI_ENDPOINT":   "controllers",
    "RULE_FLASK":              "runtime",
    "RULE_DJANGO":             "runtime",
    "RULE_EXPRESS":            "runtime",
    "RULE_AUTH_JWT":           "authentication",
    "RULE_PYDANTIC_MODEL":     "models",
    "RULE_SQLALCHEMY_MODEL":   "models",
    "RULE_SQLITE":             "database",
    "RULE_POSTGRESQL":         "database",
    "RULE_ORM_QUERY":          "repositories",
    "RULE_OLLAMA":             "llm_providers",
    "RULE_LANGCHAIN":          "ai_agents",
    "RULE_CREWAI":             "ai_agents",
    "RULE_CREWAI_AGENT":       "ai_agents",
    "RULE_VECTOR_DB":          "memory",
    "RULE_CELERY":             "workers",
    "RULE_BACKGROUND_TASK":    "workers",
    "RULE_DOCKERFILE":         "deployment",
    "RULE_DOCKER":             "deployment",
    "RULE_DOCKER_MULTI_SERVICE": "deployment",
    "RULE_GITHUB_ACTIONS":     "deployment",
    "RULE_PYTEST":             "testing",
    "RULE_JEST":               "testing",
    "RULE_REDIS":              "caching",
}

# Evidence rule_id → technology name
_EVIDENCE_TECH_MAP: Dict[str, str] = {
    "RULE_REACT":              "React",
    "RULE_TAILWIND":           "Tailwind CSS",
    "RULE_TYPESCRIPT_CODE":    "TypeScript",
    "RULE_JAVASCRIPT_CODE":    "JavaScript",
    "RULE_FASTAPI":            "FastAPI",
    "RULE_FASTAPI_ROUTER":     "FastAPI Router",
    "RULE_FASTAPI_ENDPOINT":   "FastAPI",
    "RULE_FLASK":              "Flask",
    "RULE_DJANGO":             "Django",
    "RULE_EXPRESS":            "Express.js",
    "RULE_AUTH_JWT":           "JWT",
    "RULE_PYDANTIC_MODEL":     "Pydantic",
    "RULE_SQLALCHEMY_MODEL":   "SQLAlchemy",
    "RULE_SQLITE":             "SQLite",
    "RULE_POSTGRESQL":         "PostgreSQL",
    "RULE_OLLAMA":             "Ollama",
    "RULE_LANGCHAIN":          "LangChain",
    "RULE_CREWAI":             "CrewAI",
    "RULE_CREWAI_AGENT":       "CrewAI",
    "RULE_VECTOR_DB":          "VectorDB",
    "RULE_CELERY":             "Celery",
    "RULE_DOCKERFILE":         "Docker",
    "RULE_DOCKER":             "Docker Compose",
    "RULE_GITHUB_ACTIONS":     "GitHub Actions",
    "RULE_PYTEST":             "Pytest",
    "RULE_JEST":               "Jest",
    "RULE_REDIS":              "Redis",
}

# Path-based classification keywords → layer key
_PATH_LAYER_RULES = [
    (("frontend/", "/src/", ".jsx", ".tsx", ".html", ".css", ".scss"), "presentation"),
    (("test/", "tests/", "test_", "_test", "spec/", ".test."), "testing"),
    (("dockerfile", "docker-compose", ".github/workflows/", "compose", "deploy/", ".ci."), "deployment"),
    (("router", "endpoint", "route", "api/", "routes/", "handler"), "api"),
    (("model", "schema", "db/", "database/", "orm", "migration", "alembic"), "models"),
    (("repository", "repo/", "crud", "dao/", "data_access"), "repositories"),
    (("agent", "crew", "crew_agent", "crewai", "langchain"), "ai_agents"),
    (("llm", "ollama", "openai", "inference", "provider"), "llm_providers"),
    (("prompt", "system_message", "templates/prompts"), "prompt_manager"),
    (("cache", "redis", "memory_store", "cache_engine"), "caching"),
    (("worker", "background", "task", "celery", "threading"), "workers"),
    (("scheduler", "cron", "periodic", "interval"), "schedulers"),
    (("config", "settings", "configuration", ".env", "constants", ".toml"), "configuration"),
    (("util", "helper", "utility", "utils", "common", "shared"), "services"),
    (("service", "manager", "processor", "coordinator", "integrat"), "services"),
    (("monitoring", "logging", "observability", "prometheus", "otel"), "monitoring"),
    (("planner", "planning", "agent_planner"), "planner"),
    (("retriever", "rag", "search_tool"), "retriever"),
    (("sandbox", "isolated", "container_runner"), "sandbox"),
    (("plugin", "extension", "dynamic_load"), "plugin_system"),
]


class ArchitectureEngine:
    """
    AST-driven architecture layer detection.

    Primary signal: SemanticIndex (routes, models, agents, services from AST).
    Secondary:      Evidence rules.
    Tertiary:       Path/filename heuristics (tiebreaker only).
    """

    def analyze(
        self,
        evidence: List[EvidenceRecord],
        files: List[str],
        semantic_index: Optional["SemanticIndex"] = None,
    ) -> Dict[str, Any]:
        """
        Build architecture layers.

        When semantic_index is provided, AST-derived data is the primary signal.
        Evidence and path heuristics enrich and fill gaps.
        """
        from intelligence.utils import safe_list, normalize_path

        evidence = safe_list(evidence)
        files = [normalize_path(f) for f in safe_list(files)]

        # Initialize all 16 layers
        layers: Dict[str, Dict[str, Any]] = {
            lid: {"description": desc, "files": [], "techs": []}
            for lid, label, desc in _LAYER_DEFS
        }

        # ── 1. AST-derived signals (highest priority) ──────────────────────
        if semantic_index is not None:
            self._classify_from_ast(layers, semantic_index, files)

        # ── 2. Evidence-based classification ──────────────────────────────
        for ev in evidence:
            rule_id = ev.rule_id if hasattr(ev, "rule_id") else str(ev.get("rule_id", ""))
            ev_file = ev.file_path if hasattr(ev, "file_path") else str(ev.get("file_path", ""))
            if not ev_file:
                continue

            layer_key = _EVIDENCE_LAYER_MAP.get(rule_id)
            if layer_key and layer_key in layers:
                if ev_file not in layers[layer_key]["files"]:
                    layers[layer_key]["files"].append(ev_file)
                tech = _EVIDENCE_TECH_MAP.get(rule_id)
                if tech and tech not in layers[layer_key]["techs"]:
                    layers[layer_key]["techs"].append(tech)

        # ── 3. Path-based heuristics (tiebreaker for unassigned files) ─────
        already_assigned = set()
        for layer_data in layers.values():
            already_assigned.update(layer_data["files"])

        for f in files:
            if f in already_assigned:
                continue
            layer_key = self._classify_by_path(f)
            if layer_key and layer_key in layers:
                layers[layer_key]["files"].append(f)
                already_assigned.add(f)

        # ── 4. Fill techs from semantic_index if still empty ───────────────
        if semantic_index is not None:
            self._fill_techs_from_index(layers, semantic_index)

        # ── 5. Final pass: deduplicate, cap, fill defaults ─────────────────
        return self._finalize(layers, semantic_index)

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _classify_from_ast(
        self,
        layers: Dict[str, Any],
        idx: "SemanticIndex",
        files: List[str],
    ) -> None:
        """Classify files into layers using AST-derived SemanticIndex data."""

        # Routes → api layer
        # API router files
        route_files = {r.file_path for r in idx.routes}
        for fpath in route_files:
            if fpath not in layers["api"]["files"]:
                layers["api"]["files"].append(fpath)

        # ORM/Pydantic models → models layer
        model_files = {m.file_path for m in idx.models}
        for fpath in model_files:
            if fpath not in layers["models"]["files"]:
                layers["models"]["files"].append(fpath)

        # Classifications from ast agents and services
        for svc in idx.agents_and_services:
            if svc.service_type == "agent":
                if svc.file_path not in layers["ai_agents"]["files"]:
                    layers["ai_agents"]["files"].append(svc.file_path)
            elif svc.service_type == "service":
                if svc.file_path not in layers["services"]["files"]:
                    layers["services"]["files"].append(svc.file_path)

        # Docker services → deployment layer
        if idx.docker_images or idx.docker_services:
            for f in files:
                fl = f.lower()
                if "dockerfile" in fl or "docker-compose" in fl:
                    if f not in layers["deployment"]["files"]:
                        layers["deployment"]["files"].append(f)

        # Config files → configuration layer
        for f in idx.config_files:
            if f not in layers["configuration"]["files"]:
                layers["configuration"]["files"].append(f)

        # Tech names from SemanticIndex into layer techs
        tech_names = idx.get_tech_names() if hasattr(idx, "get_tech_names") else []
        for tech in tech_names:
            tl = tech.lower()
            if tl in ("react", "vue.js", "angular", "next.js", "typescript", "javascript", "tailwindcss"):
                if tech not in layers["presentation"]["techs"]:
                    layers["presentation"]["techs"].append(tech)
            elif tl in ("fastapi", "flask", "django", "express.js"):
                if tech not in layers["api"]["techs"]:
                    layers["api"]["techs"].append(tech)
            elif tl in ("uvicorn", "gunicorn", "node.js"):
                if tech not in layers["runtime"]["techs"]:
                    layers["runtime"]["techs"].append(tech)
            elif tl in ("sqlalchemy", "postgresql", "sqlite", "mysql", "mongodb", "pydantic"):
                if tech not in layers["models"]["techs"]:
                    layers["models"]["techs"].append(tech)
            elif tl in ("crewai", "langchain", "openai", "anthropic"):
                if tech not in layers["ai_agents"]["techs"]:
                    layers["ai_agents"]["techs"].append(tech)
            elif tl in ("ollama", "litellm"):
                if tech not in layers["llm_providers"]["techs"]:
                    layers["llm_providers"]["techs"].append(tech)
            elif tl in ("chromadb", "faiss"):
                if tech not in layers["memory"]["techs"]:
                    layers["memory"]["techs"].append(tech)
            elif tl in ("docker", "docker compose", "github actions"):
                if tech not in layers["deployment"]["techs"]:
                    layers["deployment"]["techs"].append(tech)
            elif tl in ("celery", "redis"):
                if tech not in layers["workers"]["techs"]:
                    layers["workers"]["techs"].append(tech)
            elif tl in ("pytest", "jest", "vitest"):
                if tech not in layers["testing"]["techs"]:
                    layers["testing"]["techs"].append(tech)

        # Assign files not yet classified
        for fpath, file_symbols in idx.symbols.items():
            already = any(fpath in l["files"] for l in layers.values())
            if not already:
                # Check if file has any routes
                if any(s.type == "route" for s in file_symbols):
                    layers["api"]["files"].append(fpath)
                elif any(s.type == "model" for s in file_symbols):
                    layers["models"]["files"].append(fpath)
                elif any(s.type == "class" for s in file_symbols):
                    layers["services"]["files"].append(fpath)

    def _classify_by_path(self, fpath: str) -> Optional[str]:
        """Path keyword classifier — tiebreaker only."""
        path_lower = fpath.lower()
        for keywords, layer_key in _PATH_LAYER_RULES:
            if any(kw in path_lower for kw in keywords):
                return layer_key
        # Default fallback
        if path_lower.endswith(".py"):
            return "services"
        if path_lower.endswith((".ts", ".tsx", ".js", ".jsx")):
            return "presentation"
        return None

    def _fill_techs_from_index(
        self, layers: Dict[str, Any], idx: "SemanticIndex"
    ) -> None:
        """Fill empty layer techs using dependency data."""
        if not idx.python_deps and not idx.node_deps:
            return

        fill_map = {
            "presentation": [("react", "React"), ("vue", "Vue.js"), ("angular", "Angular"),
                             ("next", "Next.js"), ("tailwindcss", "Tailwind CSS")],
            "api":  [("fastapi", "FastAPI"), ("flask", "Flask"), ("django", "Django"),
                     ("express", "Express.js")],
            "models":   [("sqlalchemy", "SQLAlchemy"), ("alembic", "Alembic"),
                         ("pymongo", "MongoDB"), ("redis", "Redis")],
            "ai_agents": [("crewai", "CrewAI"), ("langchain", "LangChain"),
                          ("openai", "OpenAI"), ("anthropic", "Anthropic")],
            "llm_providers": [("ollama", "Ollama"), ("litellm", "LiteLLM")],
            "memory": [("chromadb", "ChromaDB"), ("faiss-cpu", "FAISS")],
            "testing":    [("pytest", "Pytest"), ("jest", "Jest"), ("vitest", "Vitest")],
            "workers":  [("celery", "Celery"), ("redis", "Redis")],
            "deployment": [("docker", "Docker")],
        }
        all_deps = {**idx.python_deps, **idx.node_deps}
        for layer_key, tech_list in fill_map.items():
            if layer_key in layers and not layers[layer_key]["techs"]:
                for dep_key, tech_name in tech_list:
                    if dep_key in all_deps:
                        layers[layer_key]["techs"].append(tech_name)

    def _finalize(
        self, layers: Dict[str, Any], semantic_index: Optional["SemanticIndex"]
    ) -> Dict[str, Any]:
        """Deduplicate, populate rich metadata properties, and return clean dict."""
        ALWAYS_INCLUDE = {"presentation", "api", "controllers", "services", "repositories", "models", "database"}

        # Define default static property templates
        RESP_MAP = {
            "presentation": ["Rendering layouts", "Managing user interaction", "Local UI state"],
            "api": ["Routing HTTP endpoints", "Gateway mapping", "Request validations"],
            "controllers": ["Orchestrating controllers", "Mapping route params", "Session handlers"],
            "services": ["Executing business service calculations", "API wrappers"],
            "repositories": ["Executing database query abstractions", "Data mapper CRUD"],
            "models": ["Defining database data structures", "Type declarations"],
            "database": ["Database migrations", "Raw connection pools"],
            "authentication": ["Handling sign-in requests", "Verifying token signatures"],
            "authorization": ["Checking resource access permissions", "Role bindings"],
            "caching": ["Cache keys storage", "Local caches eviction"],
            "workers": ["Executing background task queue jobs"],
            "schedulers": ["Periodic schedule executions", "Heartbeat jobs"],
            "ai_agents": ["Orchestrating AI agents teams", "Task registry executions"],
            "prompt_manager": ["Formatting prompt templates", "System template binds"],
            "memory": ["Persisting agent history", "Vector similarity retrieval"],
            "planner": ["Computing planning execution steps", "Tool routing decision tree"],
            "retriever": ["Running RAG query extensions", "Document chunk parsers"],
            "sandbox": ["Executing unsafe scripts in virtual containers"],
            "runtime": ["Running uvicorn server", "Process monitoring"],
            "plugin_system": ["Dynamic class loader hooks", "Modules load paths"],
            "llm_providers": ["Invoking OpenAI API", "Invoking Ollama local models"],
            "infrastructure": ["Terraform resource configuration", "Deployment orchestration"],
            "deployment": ["Docker container configs", "CI/CD execution pipelines"],
        }

        INPUT_MAP = {
            "presentation": "User mouse and keyboard actions",
            "api": "HTTP REST requests",
            "controllers": "Parsed route parameter dictionaries",
            "authentication": "User auth credential structures",
            "database": "SQL dialect command texts",
            "ai_agents": "Agent context prompts and schemas",
            "llm_providers": "Prompt token arrays",
        }

        OUTPUT_MAP = {
            "presentation": "HTML DOM layouts and browser logs",
            "api": "HTTP JSON responses",
            "controllers": "Service request parameter mappings",
            "database": "Raw row tuples and transaction status",
            "ai_agents": "Agent execution task records",
            "llm_providers": "Generated completion texts",
        }

        CONSUMERS_MAP = {
            "presentation": "End User / Browser",
            "api": "Presentation Layer",
            "controllers": "API Gateways",
            "services": "Controllers",
            "repositories": "Services",
            "models": "Repositories & Services",
            "database": "Repositories",
            "ai_agents": "Services",
            "llm_providers": "AI Agents",
            "memory": "AI Agents",
            "prompt_manager": "AI Agents",
        }

        PROVIDERS_MAP = {
            "presentation": "API Gateways",
            "api": "Controllers",
            "controllers": "Services",
            "services": "Repositories & LLM Providers",
            "repositories": "Database & Models",
            "database": "PostgreSQL / SQLite Engines",
            "ai_agents": "LLM Providers & Memory DBs",
            "llm_providers": "OpenAI / Ollama Host",
        }

        result: Dict[str, Any] = {}
        evidence_list = semantic_index.warnings if semantic_index else []

        for lid, label, desc in _LAYER_DEFS:
            layer = layers[lid]
            files = list(set(layer["files"]))[:30]
            techs = list(dict.fromkeys(layer["techs"]))

            if files or lid in ALWAYS_INCLUDE:
                # Count average lines of code for complexity proxy
                loc_sum = 0
                if semantic_index and hasattr(semantic_index, "total_loc"):
                    loc_sum = int(semantic_index.total_loc / max(1, len(files)))
                complexity_score = min(100.0, loc_sum / 15.0)

                # Compute risk/health
                layer_ev = [ev for ev in evidence_list if lid in ev.lower()]
                health = max(40.0, 98.0 - (8.0 * len(layer_ev)))
                risk = min(95.0, 5.0 + (12.0 * len(layer_ev)))

                result[label] = {
                    "description": desc,
                    "files": files,
                    "techs": techs,
                    # Rich properties for RI v3
                    "purpose": desc,
                    "responsibilities": RESP_MAP.get(lid, ["Executing custom business logic"]),
                    "inputs": INPUT_MAP.get(lid, "Internal method parameters"),
                    "outputs": OUTPUT_MAP.get(lid, "Data object return values"),
                    "dependencies": techs if techs else ["Python Stdlib"],
                    "consumers": [CONSUMERS_MAP.get(lid, "Upstream caller modules")],
                    "providers": [PROVIDERS_MAP.get(lid, "Downstream helper modules")],
                    "complexity": round(complexity_score, 1),
                    "health": round(health, 1),
                    "risk": round(risk, 1),
                    "ownership": "Core Engineering Team",
                    "evidence": layer_ev,
                    "confidence": 0.95 if files else 0.70,
                    "summary": f"Deterministic architecture layer representing {label}."
                }

        return result

