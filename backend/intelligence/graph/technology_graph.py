"""
technology_graph.py — AST and manifest-driven technology graph.

Constructs technology graph showing detected technologies, their categories,
confidence scores, versions, and rich contextual metadata:
- Related files (which files import/use this technology)
- Related APIs (which routes were detected via this tech's decorators)
- Related services (service/agent classes using this tech)
- Related databases (data stores connected to this tech)
- Related Docker images/services
- Detection reason (human-readable explanation)
- Alternative technologies
"""
from __future__ import annotations

from typing import List, Dict, Any, Union, Set
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder
from intelligence.semantic_index import TechDetection, SemanticIndex


# Relationship definitions — (source_tech, dest_tech, label)
TECH_RELATIONS = [
    # Frontend
    ("react", "vite", "bundled by"),
    ("react", "typescript", "written in"),
    ("react", "tailwind css", "styled with"),
    ("react", "next.js", "extended by"),
    ("next.js", "react", "extends"),
    ("next.js", "typescript", "uses"),
    # Backend / API
    ("fastapi", "sqlalchemy", "queries via"),
    ("fastapi", "pydantic", "serializes via"),
    ("fastapi", "python", "runs on"),
    ("fastapi", "uvicorn", "served by"),
    ("flask", "python", "runs on"),
    ("django", "python", "runs on"),
    ("django", "sqlalchemy", "queries via"),
    ("express.js", "node.js", "runs on"),
    ("express.js", "typescript", "written in"),
    # DB / Data
    ("sqlalchemy", "postgresql", "persists in"),
    ("sqlalchemy", "sqlite", "persists in"),
    ("sqlalchemy", "mysql", "persists in"),
    ("redis", "python", "accessed from"),
    ("chromadb", "python", "accessed from"),
    # ML / AI / Agents
    ("crewai", "ollama", "runs local inference on"),
    ("crewai", "openai", "invokes"),
    ("crewai", "langchain", "orchestrates tools via"),
    ("langchain", "ollama", "orchestrates"),
    ("langchain", "openai", "invokes"),
    ("langchain", "chromadb", "stores vectors in"),
    ("openai", "python", "accessed via"),
    ("ollama", "python", "accessed via"),
    # Testing
    ("pytest", "python", "tests"),
    # Infra
    ("docker compose", "docker", "groups containers of"),
    ("python", "docker", "containerized in"),
    ("node.js", "docker", "containerized in"),
    ("go", "docker", "containerized in"),
]

# Human-readable edge explanations
EDGE_EXPLANATIONS = {
    ("react", "vite"): "React modules are bundled and served via Vite's dev server for hot module reloading and optimized production builds.",
    ("react", "typescript"): "React components are statically typed using TypeScript, providing compile-time safety and IDE intelligence.",
    ("react", "tailwind css"): "React UI elements are styled using Tailwind CSS utility classes compiled at build time.",
    ("fastapi", "pydantic"): "FastAPI uses Pydantic models to automatically validate and serialize all incoming request bodies and outgoing responses.",
    ("fastapi", "sqlalchemy"): "FastAPI route handlers access the database through SQLAlchemy ORM sessions injected as dependencies.",
    ("fastapi", "python"): "FastAPI is a Python web framework; all routes, middleware, and handlers run in the Python runtime.",
    ("fastapi", "uvicorn"): "FastAPI applications are served by Uvicorn, an ASGI server providing async HTTP handling.",
    ("sqlalchemy", "sqlite"): "SQLAlchemy maps ORM entities to SQLite tables for lightweight local persistence.",
    ("sqlalchemy", "postgresql"): "SQLAlchemy maps ORM entities to PostgreSQL tables for production-grade persistence.",
    ("crewai", "openai"): "CrewAI routes agent reasoning and tool calls through the OpenAI language model API.",
    ("crewai", "langchain"): "CrewAI uses LangChain tool bindings and loaders to extend agent capabilities.",
    ("crewai", "ollama"): "CrewAI runs local model inference through the Ollama server API for offline agent execution.",
    ("langchain", "chromadb"): "LangChain stores and retrieves embedding vectors in ChromaDB for semantic memory and RAG pipelines.",
    ("docker compose", "docker"): "Docker Compose defines and orchestrates multiple Docker container services as a unified application.",
    ("python", "docker"): "The Python application environment is built and runs inside a Docker container for reproducible deployments.",
}

# Common alternative technologies per category
TECH_ALTERNATIVES = {
    "fastapi": ["Flask", "Django", "Litestar", "Starlette"],
    "flask": ["FastAPI", "Django", "Bottle", "Starlette"],
    "django": ["FastAPI", "Flask", "Litestar"],
    "react": ["Vue.js", "Angular", "Svelte", "SolidJS"],
    "next.js": ["Nuxt.js", "SvelteKit", "Remix", "Astro"],
    "sqlalchemy": ["Tortoise ORM", "Peewee", "Django ORM", "Prisma"],
    "postgresql": ["MySQL", "SQLite", "MongoDB", "CockroachDB"],
    "redis": ["Memcached", "DragonflyDB", "KeyDB"],
    "chromadb": ["Pinecone", "Weaviate", "Qdrant", "FAISS"],
    "langchain": ["LlamaIndex", "Haystack", "Semantic Kernel"],
    "crewai": ["AutoGen", "LangGraph", "Agency Swarm", "Phidata"],
    "openai": ["Anthropic Claude", "Ollama", "Gemini", "Mistral"],
    "ollama": ["LocalAI", "LM Studio", "vLLM", "Llamafile"],
    "pytest": ["unittest", "nose2", "hypothesis"],
    "docker": ["Podman", "Buildah", "containerd"],
    "celery": ["RQ", "Dramatiq", "APScheduler", "Huey"],
}

# Tech category to runtime environment mapping
TECH_RUNTIME = {
    "FRAMEWORK": "Application Runtime",
    "LANGUAGE": "Interpreter/Compiler",
    "DATABASE": "Data Persistence Layer",
    "ML": "AI/ML Inference Engine",
    "TOOL": "Developer Tooling",
    "CLOUD": "Cloud Infrastructure",
    "RUNTIME": "Runtime Environment",
}


class TechnologyGraphBuilder(BaseGraphBuilder):
    """
    Constructs Technology Graph listing detected stack components.
    Emits rich, contextual node metadata per technology:
    - Files using the technology
    - APIs/routes detected via the technology
    - Services/agents related to the technology
    - Detection reason
    - Alternatives
    - Docker images / services
    - Related databases
    """

    def build(
        self,
        techs: List[Union[str, TechDetection, Dict[str, Any]]],
        semantic_index: "SemanticIndex | None" = None,
    ) -> None:
        self.nodes = []
        self.edges = []

        node_ids: Set[str] = set()
        # Pre-index the semantic context if provided
        si = semantic_index

        for t in techs:
            # Normalize input format
            if hasattr(t, "name"):
                name = t.name
                confidence = getattr(t, "confidence", 1.0)
                category = getattr(t, "category", "FRAMEWORK")
                version = getattr(t, "version", None)
                sources = getattr(t, "sources", [])
            elif isinstance(t, dict):
                name = t.get("name") or t.get("label", "unknown")
                confidence = t.get("confidence", 1.0)
                category = t.get("category", "FRAMEWORK")
                version = t.get("version", None)
                sources = t.get("sources", [])
            else:
                name = str(t)
                confidence = 1.0
                category = "FRAMEWORK"
                version = None
                sources = []

            node_id = name.lower()
            if node_id in node_ids:
                continue
            node_ids.add(node_id)

            # Build rich contextual metadata from SemanticIndex
            related_files: List[str] = []
            related_apis: List[str] = []
            related_services: List[str] = []
            related_databases: List[str] = []
            related_docker: List[str] = []
            related_agents: List[str] = []
            detection_reason = f"Detected via {', '.join(sources) or 'code analysis'}."

            if si:
                name_lower = name.lower()
                # Files that import this technology
                for fpath, imports in si.imports.items():
                    if any(name_lower in imp.lower() for imp in imports):
                        if fpath not in related_files:
                            related_files.append(fpath)

                # APIs belonging to this tech's framework
                if name_lower in ("fastapi", "flask", "django", "express.js", "express"):
                    for route in si.routes:
                        route_info = f"{route.method} {route.path or ''} ({route.function_name})"
                        if route_info not in related_apis:
                            related_apis.append(route_info)

                # Services and agents using this tech
                for svc in si.agents_and_services:
                    svc_file_content_imports = si.imports.get(svc.file_path, [])
                    if any(name_lower in imp.lower() for imp in svc_file_content_imports):
                        svc_info = f"{svc.service_type.capitalize()}: {svc.name}"
                        if svc_info not in related_services:
                            related_services.append(svc_info)
                    # AI agent detection
                    if svc.service_type in ("agent", "crew") and name_lower in (
                        "crewai", "langchain", "openai", "ollama", "langchain_openai"
                    ):
                        agent_info = f"{svc.name} ({svc.file_path.split('/')[-1]})"
                        if agent_info not in related_agents:
                            related_agents.append(agent_info)

                # Database relations
                if category == "DATABASE" or name_lower in (
                    "sqlalchemy", "postgresql", "sqlite", "mysql", "chromadb", "redis", "mongodb"
                ):
                    for model in si.models:
                        if model.model_type in ("orm", "pydantic"):
                            db_info = f"Model: {model.name} ({model.file_path.split('/')[-1]})"
                            if db_info not in related_databases:
                                related_databases.append(db_info)

                # Docker relations
                for img in si.docker_images:
                    if name_lower in img.lower():
                        if img not in related_docker:
                            related_docker.append(img)
                for svc_name in si.docker_services:
                    if name_lower in svc_name.lower():
                        if svc_name not in related_docker:
                            related_docker.append(f"service: {svc_name}")

                # Enrich detection reason
                source_labels = {
                    "requirements.txt": "requirements.txt manifest",
                    "package.json": "package.json manifest",
                    "pyproject.toml": "pyproject.toml manifest",
                    "go.mod": "go.mod manifest",
                    "import": f"{len(related_files)} source file import(s)",
                    "route_decorators": "route decorator analysis",
                    "file_extensions": "file extension analysis",
                    "dockerfile": "Dockerfile FROM statement",
                    "docker_compose": "docker-compose.yml service definition",
                    "agent_class": "agent/crew class detection",
                }
                readable_sources = [source_labels.get(s, s) for s in sources]
                if readable_sources:
                    detection_reason = f"Detected via {', '.join(readable_sources[:3])}."
                if related_files:
                    detection_reason += f" Found in {len(related_files)} file(s)."

            metadata: Dict[str, Any] = {
                "confidence": round(confidence, 3),
                "category": category,
                "version": version or "unknown",
                "sources": sources[:5],  # Detection source file(s)
                "description": f"{category.capitalize()} component: {name}. {TECH_RUNTIME.get(category, 'Runtime')}.",
                "detection_reason": detection_reason,
                "related_files": related_files[:20],  # Cap for payload size
                "related_apis": related_apis[:15],
                "related_services": related_services[:10],
                "related_databases": related_databases[:10],
                "related_docker": related_docker[:8],
                "related_agents": related_agents[:10],
                "alternatives": TECH_ALTERNATIVES.get(node_id, []),
                "runtime": TECH_RUNTIME.get(category, "Application Runtime"),
            }

            self.nodes.append(GraphNode(
                id=node_id,
                label=name,
                type="technology",
                metadata=metadata,
            ))

        # Add connection edges based on relation definitions
        for src, dest, label in TECH_RELATIONS:
            if src in node_ids and dest in node_ids:
                key = (src, dest)
                why = EDGE_EXPLANATIONS.get(
                    key,
                    f"{src.capitalize()} connects to {dest.capitalize()} as part of the integrated technology stack.",
                )
                self.edges.append(GraphEdge(
                    source=src,
                    target=dest,
                    label=label,
                    metadata={"why": why},
                ))
