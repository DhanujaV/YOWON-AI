"""
knowledge_graph_builder.py — AST and semantic-driven knowledge graph construction.

Constructs semantic nodes and relationships (Route, Service, Model, Agent, Env Var, Library)
instead of just file-to-file circles.
"""
from __future__ import annotations

import re
import json
import logging
from typing import Dict, List, Any, Set, Tuple, Optional

from intelligence.models import SymbolRecord
from intelligence.semantic_index import SemanticIndex

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    def __init__(self):
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []
        self.node_ids: Set[str] = set()

    def add_node(self, node_id: str, label: str, node_type: str, metadata: Dict[str, Any] = None) -> None:
        clean_id = node_id.strip()
        if not clean_id or clean_id in self.node_ids:
            return
        self.node_ids.add(clean_id)
        self.nodes.append({
            "id": clean_id,
            "label": label.strip(),
            "type": node_type,
            "metadata": metadata or {}
        })

    def add_edge(self, source: str, target: str, relation: str) -> None:
        src = source.strip()
        tgt = target.strip()
        if src in self.node_ids and tgt in self.node_ids and src != tgt:
            edge_exists = any(
                e["source"] == src and e["target"] == tgt and e["relation"] == relation
                for e in self.edges
            )
            if not edge_exists:
                self.edges.append({
                    "source": src,
                    "target": tgt,
                    "relation": relation
                })

    def build_graph(
        self,
        files: List[str],
        file_contents: Dict[str, str],
        symbols: List[SymbolRecord],
        evidence: List[Any] = None,
        recommendations: List[Any] = None,
        semantic_index: Optional[SemanticIndex] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        self.nodes.clear()
        self.edges.clear()
        self.node_ids.clear()

        # ── 1. Path normalization at entry point ──────────────────────────────
        from intelligence.repository_scan import RepositoryScan
        clean_files = [RepositoryScan.normalize_path(f) for f in files]
        clean_file_contents = {RepositoryScan.normalize_path(k): v for k, v in file_contents.items()}

        clean_symbols = []
        for sym in symbols:
            # Reconstruct sym with normalized path
            clean_symbols.append(SymbolRecord(
                name=sym.name,
                type=sym.type,
                file_path=RepositoryScan.normalize_path(sym.file_path),
                line_start=sym.line_start,
                line_end=sym.line_end,
                column_start=sym.column_start,
                column_end=sym.column_end,
                relationships=sym.relationships
            ))

        evidence_list = []
        for ev in (evidence or []):
            if isinstance(ev, dict):
                ev_copy = dict(ev)
                ev_copy["file_path"] = RepositoryScan.normalize_path(ev.get("file_path", ""))
                evidence_list.append(ev_copy)
            elif hasattr(ev, "file_path"):
                evidence_list.append({
                    "rule_id": getattr(ev, "rule_id", ""),
                    "file_path": RepositoryScan.normalize_path(getattr(ev, "file_path", ""))
                })

        rec_list = []
        for rec in (recommendations or []):
            if isinstance(rec, dict):
                rec_copy = dict(rec)
                rec_copy["affected_files"] = [RepositoryScan.normalize_path(f) for f in rec.get("affected_files", [])]
                rec_list.append(rec_copy)

        # ── 2. Create Level 1 Root and Subsystem/Capability Nodes ───────────────────
        repo_name = clean_files[0].split("/")[0] if clean_files else "SentinelProject"
        repo_id = f"repo::{repo_name}"
        self.add_node(
            node_id=repo_id,
            label=repo_name,
            node_type="repository",
            metadata={"description": "Root Repository Node", "level": 1}
        )

        # Retrieve capabilities from semantic index
        caps = semantic_index.capabilities if (semantic_index and hasattr(semantic_index, "capabilities")) else []
        for cap in caps:
            cap_id = f"cap::{cap.lower()}"
            self.add_node(
                node_id=cap_id,
                label=cap,
                node_type="capability",
                metadata={"description": f"Repository architectural capability: {cap}", "level": 1}
            )
            # Link root to capabilities
            self.add_edge(source=repo_id, target=cap_id, relation="HAS_CAPABILITY")

        # Create Subsystem nodes corresponding to active subsystems
        subsystems_defs = [
            ("presentation", "Presentation Layer"),
            ("api", "API Gateways"),
            ("controllers", "Route Controllers"),
            ("services", "Business Services"),
            ("repositories", "Data Repositories"),
            ("models", "ORM Models"),
            ("database", "Relational Database"),
            ("caching", "Cache store"),
            ("workers", "Workers & Background Tasks"),
            ("schedulers", "Schedulers & Cron"),
            ("ai_agents", "AI Agent System"),
            ("prompt_manager", "Prompt templates"),
            ("memory", "Agent Memory & VectorDB"),
            ("llm_providers", "LLM Providers"),
            ("deployment", "CI/CD & DevOps"),
            ("testing", "Testing Suite"),
            ("configuration", "Configuration & Env"),
        ]

        for sid, label in subsystems_defs:
            sub_id = f"sub::{sid}"
            self.add_node(
                node_id=sub_id,
                label=label,
                node_type="subsystem",
                metadata={"description": f"Architectural Subsystem: {label}", "level": 1}
            )
            # Link repository root to subsystems
            self.add_edge(source=repo_id, target=sub_id, relation="CONTAINS")

        # ── 3. Add File Nodes ────────────────────────────────────────────────────────
        for fpath in clean_files:
            ext = fpath.split(".")[-1].lower() if "." in fpath else ""
            
            # Map file to subsystem
            sid = "services"
            fl = fpath.lower()
            if "frontend" in fl or "/src" in fl and ext in ("ts", "tsx", "js", "jsx"):
                sid = "presentation"
            elif "tests" in fl or "test" in fl or "spec" in fl:
                sid = "testing"
            elif "docker" in fl or "compose" in fl or ".github/workflows" in fl:
                sid = "deployment"
            elif "route" in fl or "endpoint" in fl or "api" in fl:
                sid = "api"
            elif "model" in fl or "schema" in fl or "db" in fl:
                sid = "models"
            elif "agent" in fl or "crew" in fl:
                sid = "ai_agents"

            self.add_node(
                node_id=fpath,
                label=fpath.split("/")[-1],
                node_type="file",
                metadata={"description": f"Source file: {fpath}", "level": 2}
            )
            # Link subsystem to file
            self.add_edge(source=f"sub::{sid}", target=fpath, relation="CONTAINS")

        # ── 4. Add Level 2 Component Nodes (Services, APIs, Workers, Databases, Agents, Tools) ─────
        # For each symbol, classify into Level 2
        for sym in clean_symbols:
            sym_id = f"{sym.file_path}::{sym.name}"
            ntype = sym.type if sym.type else "service"

            if sym.type == "route":
                ntype = "route"
            elif sym.type == "model":
                ntype = "model"
            elif "worker" in sym.name.lower() or "celery" in sym.name.lower():
                ntype = "worker"
            elif "agent" in sym.name.lower() or "crew" in sym.name.lower():
                ntype = "agent"
            elif "tool" in sym.name.lower():
                ntype = "tool"

            # Check if subclass inherits from tool or agent
            for rel in sym.relationships:
                if rel.get("type") == "extends":
                    base = rel.get("target", "").lower()
                    if "agent" in base:
                        ntype = "agent"
                    elif "tool" in base:
                        ntype = "tool"

            self.add_node(
                node_id=sym_id,
                label=sym.name,
                node_type=ntype,
                metadata={
                    "file_path": sym.file_path,
                    "line_start": sym.line_start,
                    "line_end": sym.line_end,
                    "description": f"Semantic components: {sym.name} ({ntype})",
                    "level": 2
                }
            )
            # Link File to Symbol
            if sym.file_path in clean_files:
                self.add_edge(source=sym.file_path, target=sym_id, relation="DEFINES")

        # ── 4. Add Level 3 Class/Function Nodes (Revealed on Drill-Down) ──────────
        for sym in clean_symbols:
            sym_id = f"{sym.file_path}::{sym.name}"
            
            # If class, register its methods/functions as Level 3 nodes
            if sym.type == "class":
                # Find functions defined in the same file that are part of this class
                for other in clean_symbols:
                    if other.type == "function" and other.file_path == sym.file_path and other.line_start > sym.line_start and other.line_end < sym.line_end:
                        child_id = f"{other.file_path}::{sym.name}.{other.name}"
                        self.add_node(
                            node_id=child_id,
                            label=f"{sym.name}.{other.name}",
                            node_type="function",
                            metadata={
                                "file_path": other.file_path,
                                "line_start": other.line_start,
                                "level": 3,
                                "parent_class": sym.name
                            }
                        )
                        # Link Level 2 to Level 3
                        self.add_edge(source=sym_id, target=child_id, relation="DEFINES_METHOD")

        # ── 5. Parse environment variables & docker compose ──────────────────
        env_vars_detected = set()
        env_var_pattern = re.compile(r'(?:os\.environ\.get|os\.getenv)\(\s*["\']([A-Z0-9_]+)["\']')
        for fpath, content in clean_file_contents.items():
            for var in env_var_pattern.findall(content):
                env_vars_detected.add(var)
                var_id = f"env::{var}"
                self.add_node(
                    node_id=var_id,
                    label=var,
                    node_type="env_var",
                    metadata={"description": f"Config environment variable used in {fpath}."}
                )
                self.add_edge(source=fpath, target=var_id, relation="READS")
                # Link to config component
                self.add_edge(source="sub::configuration", target=var_id, relation="EXPOSES")

        # Parse Docker compose services
        for fpath, content in clean_file_contents.items():
            if "docker-compose" in fpath.lower() or "compose.yml" in fpath.lower() or "compose.yaml" in fpath.lower():
                lines = content.splitlines()
                in_services = False
                for line in lines:
                    indent = len(line) - len(line.lstrip())
                    stripped = line.strip()
                    if stripped.startswith("services:"):
                        in_services = True
                        continue
                    if in_services:
                        if stripped and not stripped.startswith("#"):
                            if ":" in stripped and indent == 2:
                                svc_name = stripped.split(":")[0].strip()
                                svc_id = f"docker::{svc_name}"
                                self.add_node(
                                    node_id=svc_id,
                                    label=svc_name,
                                    node_type="docker_service",
                                    metadata={
                                        "description": f"Docker container service defined in {fpath}."
                                    }
                                )
                                self.add_edge(source=fpath, target=svc_id, relation="DEFINES")
                                self.add_edge(source="sub::deployment", target=svc_id, relation="EXPOSES")
                            elif indent == 0 and stripped:
                                in_services = False

        # Libraries & Imports
        libraries_detected = set()
        for fpath, content in clean_file_contents.items():
            if fpath.endswith("requirements.txt"):
                for line in content.splitlines():
                    clean_line = line.strip().split("==")[0].split(">=")[0].strip()
                    if clean_line and not clean_line.startswith("#"):
                        libraries_detected.add(clean_line)
                        lib_id = f"lib::{clean_line}"
                        self.add_node(
                            node_id=lib_id,
                            label=clean_line,
                            node_type="library",
                            metadata={"description": "External Python package dependency."}
                        )
                        self.add_edge(source=fpath, target=lib_id, relation="DEPENDS_ON")
            elif fpath.endswith("package.json"):
                try:
                    pjson = json.loads(content)
                    deps = {**pjson.get("dependencies", {}), **pjson.get("devDependencies", {})}
                    for lib in deps:
                        libraries_detected.add(lib)
                        lib_id = f"lib::{lib}"
                        self.add_node(
                            node_id=lib_id,
                            label=lib,
                            node_type="library",
                            metadata={"description": "External Node.js package dependency."}
                        )
                        self.add_edge(source=fpath, target=lib_id, relation="DEPENDS_ON")
                except Exception:
                    pass

        # ── 6. Semantic edges (Route→Service, Service→Model, Agent→LLM) ────────
        # Scan file content to build AST edges between symbols
        for sym in clean_symbols:
            sym_id = f"{sym.file_path}::{sym.name}"
            content = clean_file_contents.get(sym.file_path, "")
            if not content:
                continue

            # Extract the actual lines of code for this symbol
            lines = content.splitlines()[sym.line_start - 1 : sym.line_end]
            symbol_code = "\n".join(lines).lower()

            # If Route -> check if it calls any Service class or contains service names
            is_route = any(n["id"] == sym_id and n["type"] == "route" for n in self.nodes)
            if is_route:
                for other in self.nodes:
                    if other["type"] == "class" and other["id"] != sym_id:
                        other_name = other["label"].lower()
                        if other_name in symbol_code:
                            self.add_edge(source=sym_id, target=other["id"], relation="CALLS")

            # If Service/Agent -> check if it uses any Model
            is_service_or_agent = any(n["id"] == sym_id and n["type"] in ("class", "agent") for n in self.nodes)
            if is_service_or_agent:
                for other in self.nodes:
                    if other["type"] == "model" and other["id"] != sym_id:
                        other_name = other["label"].lower()
                        if other_name in symbol_code:
                            self.add_edge(source=sym_id, target=other["id"], relation="MUTATES")

            # If Agent -> check if it uses Ollama or LLM library
            is_agent = any(n["id"] == sym_id and n["type"] == "agent" for n in self.nodes)
            if is_agent:
                for target_lib in ("ollama", "openai", "langchain"):
                    lib_id = f"lib::{target_lib}"
                    if lib_id in self.node_ids:
                        self.add_edge(source=sym_id, target=lib_id, relation="INVOKES")

        return self.nodes, self.edges
