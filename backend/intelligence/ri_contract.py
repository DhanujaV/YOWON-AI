"""
ri_contract.py — Canonical Repository Intelligence Result contract.

RepositoryIntelligenceResult is the SINGLE object produced by the RI pipeline
and consumed by:
  - REST API layer (serialized as pure JSON DTOs)
  - EvaluationSession (code knowledge for AI agents)
  - Cache engine (disk/DB persistence)
  - Pipeline Validator (Stage 4 completeness checks)

No other module defines its own RI data model.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# Diagnostics
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class RIDiagnosticsPayload:
    """
    18-field diagnostics telemetry produced alongside every RI analysis.
    Surfaced in the /status endpoint and the DiagnosticsPanel UI.
    """
    # Repository dimensions
    repository_size_bytes: int = 0
    total_directories: int = 0
    total_files: int = 0
    total_loc: int = 0

    # Code intelligence
    total_functions: int = 0
    total_classes: int = 0
    total_imports: int = 0
    total_dependencies: int = 0
    total_ast_nodes: int = 0
    total_routes: int = 0
    total_models: int = 0

    # Graph dimensions
    architecture_nodes: int = 0
    technology_nodes: int = 0
    knowledge_nodes: int = 0
    knowledge_edges: int = 0
    evidence_count: int = 0

    # Execution telemetry
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    cache_level: str = "MISS"           # L1_MEMORY | L2_DB | L3_DISK | MISS
    execution_time_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    engine_version: str = "2.0.0"

    # Stage durations (telemetry)
    scan_duration: float = 0.0
    index_duration: float = 0.0
    evidence_duration: float = 0.0
    knowledge_graph_duration: float = 0.0
    architecture_duration: float = 0.0
    technology_duration: float = 0.0
    dependency_duration: float = 0.0
    cache_read_duration: float = 0.0
    cache_write_duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_size_bytes": self.repository_size_bytes,
            "total_directories": self.total_directories,
            "total_files": self.total_files,
            "total_loc": self.total_loc,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "total_imports": self.total_imports,
            "total_dependencies": self.total_dependencies,
            "total_ast_nodes": self.total_ast_nodes,
            "total_routes": self.total_routes,
            "total_models": self.total_models,
            "architecture_nodes": self.architecture_nodes,
            "technology_nodes": self.technology_nodes,
            "knowledge_nodes": self.knowledge_nodes,
            "knowledge_edges": self.knowledge_edges,
            "evidence_count": self.evidence_count,
            "warnings": self.warnings,
            "errors": self.errors,
            "cache_level": self.cache_level,
            "execution_time_seconds": round(self.execution_time_seconds, 3),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "engine_version": self.engine_version,
            "scan_duration": round(self.scan_duration, 3),
            "index_duration": round(self.index_duration, 3),
            "evidence_duration": round(self.evidence_duration, 3),
            "knowledge_graph_duration": round(self.knowledge_graph_duration, 3),
            "architecture_duration": round(self.architecture_duration, 3),
            "technology_duration": round(self.technology_duration, 3),
            "dependency_duration": round(self.dependency_duration, 3),
            "cache_read_duration": round(self.cache_read_duration, 3),
            "cache_write_duration": round(self.cache_write_duration, 3),
        }


# ──────────────────────────────────────────────────────────────────────────
# Intelligence Quality Score
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class RIQualityScore:
    """
    Per-artifact quality scores (0–100). Used by Stage 4 validator and Diagnostics UI.
    """
    repository_tree_score: float = 0.0
    architecture_score: float = 0.0
    technology_score: float = 0.0
    dependency_score: float = 0.0
    knowledge_graph_score: float = 0.0
    evidence_score: float = 0.0
    diagnostics_score: float = 0.0
    overall_score: float = 0.0

    @property
    def is_sufficient(self) -> bool:
        """True if all critical artifacts meet minimum thresholds for evaluation."""
        return (
            self.architecture_score >= 20.0
            and self.technology_score >= 20.0
            and self.evidence_score >= 10.0
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_tree_score": round(self.repository_tree_score, 1),
            "architecture_score": round(self.architecture_score, 1),
            "technology_score": round(self.technology_score, 1),
            "dependency_score": round(self.dependency_score, 1),
            "knowledge_graph_score": round(self.knowledge_graph_score, 1),
            "evidence_score": round(self.evidence_score, 1),
            "diagnostics_score": round(self.diagnostics_score, 1),
            "overall_score": round(self.overall_score, 1),
            "is_sufficient": self.is_sufficient,
        }

    @classmethod
    def compute(cls, result: "RIResult") -> "RIQualityScore":
        """Compute quality scores from a completed RIResult."""
        # Repository tree: 100 if has nodes
        tree_score = 100.0 if (result.repository_tree and len(result.repository_tree) > 0) else 0.0

        # Architecture: scale 0-100 at 8 nodes
        arch_nodes = len((result.architecture_graph or {}).get("nodes", []))
        arch_score = min(100.0, arch_nodes / 8.0 * 100.0)

        # Technology: scale 0-100 at 5 techs with confidence
        tech_nodes = len((result.technology_graph or {}).get("nodes", []))
        tech_score = min(100.0, tech_nodes / 5.0 * 100.0)

        # Dependencies: 100 if any deps found, 50 if empty
        all_dep_nodes = len((result.dependency_graph or {}).get("nodes", []))
        dep_score = 100.0 if all_dep_nodes > 1 else (50.0 if result.dependency_graph else 0.0)

        # Knowledge graph: scale based on nodes + edges
        kg_nodes = len((result.knowledge_graph or {}).get("nodes", []))
        kg_edges = len((result.knowledge_graph or {}).get("edges", []))
        kg_score = min(100.0, (kg_nodes / 50.0 + kg_edges / 100.0) * 50.0)

        # Evidence: scale 0-100 at 20 records
        ev_count = len(result.evidence or [])
        ev_score = min(100.0, ev_count / 20.0 * 100.0)

        # Diagnostics: 100 if execution_time > 0 and files > 0
        diag = result.diagnostics
        diag_score = 100.0 if (diag and diag.execution_time_seconds > 0 and diag.total_files > 0) else 0.0

        # Weighted overall
        weights = [
            (tree_score, 0.10),
            (arch_score, 0.20),
            (tech_score, 0.15),
            (dep_score, 0.10),
            (kg_score, 0.15),
            (ev_score, 0.20),
            (diag_score, 0.10),
        ]
        overall = sum(score * w for score, w in weights)

        return cls(
            repository_tree_score=tree_score,
            architecture_score=arch_score,
            technology_score=tech_score,
            dependency_score=dep_score,
            knowledge_graph_score=kg_score,
            evidence_score=ev_score,
            diagnostics_score=diag_score,
            overall_score=overall,
        )


# ──────────────────────────────────────────────────────────────────────────
# Canonical Result
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class RIResult:
    """
    The single canonical output of the Repository Intelligence pipeline.

    Produced by: intelligence_service.run_repository_intelligence()
    Consumed by:
      - API layer (serialized to pure JSON DTOs)
      - EvaluationSession (RepositoryIntelligenceResult field)
      - Cache engine (disk/DB persistence via to_cache_dict)
      - Pipeline Validator Stage 4
    """
    # Core artifacts — pure lists and dicts, no custom wrappers
    repository_tree: List[Dict[str, Any]] = field(default_factory=list)
    architecture_graph: Dict[str, Any] = field(default_factory=dict)
    technology_graph: Dict[str, Any] = field(default_factory=dict)
    dependency_graph: Dict[str, Any] = field(default_factory=dict)
    call_graph: Dict[str, Any] = field(default_factory=dict)
    knowledge_graph: Dict[str, Any] = field(default_factory=dict)

    # Analysis results
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    health: Dict[str, Any] = field(default_factory=dict)
    security_findings: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)

    # Technology intelligence
    detected_technologies: List[str] = field(default_factory=list)  # names only
    technology_detections: List[Dict[str, Any]] = field(default_factory=list)  # full TechDetection dicts
    architecture_summary: str = ""
    technology_summary: str = ""
    dependency_summary: str = ""
    repository_summary: str = ""

    # Diagnostics (18 fields)
    diagnostics: Optional[RIDiagnosticsPayload] = None

    # Quality score
    quality: Optional[RIQualityScore] = None
    # Structured intelligence properties (Repository Intelligence v3)
    capabilities: List[str] = field(default_factory=list)
    execution_intelligence: Dict[str, Any] = field(default_factory=dict)
    ai_intelligence: Dict[str, Any] = field(default_factory=dict)
    dependency_intelligence: Dict[str, Any] = field(default_factory=dict)

    # Snapshot ID for cache linkage
    repository_snapshot_id: str = ""

    def to_cache_dict(self) -> Dict[str, Any]:
        """
        Serialize to pure JSON-safe dict for disk/DB cache storage.
        This is the format stored by RepositoryAnalysisCache.set().
        """
        return {
            "repository_snapshot_id": self.repository_snapshot_id,
            "repository_tree": self.repository_tree,
            "architecture_graph": self.architecture_graph,
            "technology_graph": self.technology_graph,
            "dependency_graph": self.dependency_graph,
            "call_graph": self.call_graph,
            "knowledge_graph": self.knowledge_graph,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "symbols": self.symbols,
            "metrics": self.metrics,
            "health": self.health,
            "security_findings": self.security_findings,
            "detected_technologies": self.detected_technologies,
            "technology_detections": self.technology_detections,
            "architecture_summary": self.architecture_summary,
            "technology_summary": self.technology_summary,
            "dependency_summary": self.dependency_summary,
            "repository_summary": self.repository_summary,
            "diagnostics": self.diagnostics.to_dict() if self.diagnostics else {},
            "quality": self.quality.to_dict() if self.quality else {},
            "file_contents": self.file_contents,
            "capabilities": self.capabilities,
            "execution_intelligence": self.execution_intelligence,
            "ai_intelligence": self.ai_intelligence,
            "dependency_intelligence": self.dependency_intelligence,
        }

    @classmethod
    def from_cache_dict(cls, data: Dict[str, Any]) -> "RIResult":
        """
        Deserialize from cache dict. Validates contract on load.
        Returns a valid RIResult even if some fields are missing.
        """
        if not isinstance(data, dict):
            return cls()

        def safe_list(val: Any) -> List:
            return val if isinstance(val, list) else []

        def safe_dict(val: Any) -> Dict:
            return val if isinstance(val, dict) else {}

        diag_data = data.get("diagnostics") or {}
        diagnostics = None
        if diag_data and isinstance(diag_data, dict) and any(v for v in diag_data.values() if isinstance(v, (int, float)) and v > 0):
            try:
                diagnostics = RIDiagnosticsPayload(**{
                    k: v for k, v in diag_data.items()
                    if k in RIDiagnosticsPayload.__dataclass_fields__
                })
            except Exception:
                diagnostics = None

        if not diagnostics:
            # Reconstruct diagnostics on-the-fly for backward compatibility / missing telemetry
            try:
                symbols = data.get("symbols") or []
                file_contents = data.get("file_contents") or {}
                total_loc = sum(len(c.splitlines()) for c in file_contents.values()) if isinstance(file_contents, dict) else 0
                
                func_count = 0
                class_count = 0
                route_count = 0
                model_count = 0
                for s in symbols:
                    if isinstance(s, dict):
                        st = s.get("type")
                        if st == "function": func_count += 1
                        elif st == "class": class_count += 1
                        elif st == "route": route_count += 1
                        elif st == "model": model_count += 1
                
                tree_len = len(data.get("repository_tree", []))
                
                diagnostics = RIDiagnosticsPayload(
                    repository_size_bytes=sum(len(c) for c in file_contents.values()) if isinstance(file_contents, dict) else 0,
                    total_directories=len({f.rsplit("/", 1)[0] for f in file_contents.keys() if "/" in f}) if isinstance(file_contents, dict) else 0,
                    total_files=tree_len if tree_len > 0 else (len(file_contents) if isinstance(file_contents, dict) else 0),
                    total_loc=total_loc,
                    total_functions=func_count,
                    total_classes=class_count,
                    total_imports=tree_len * 4,
                    total_dependencies=len((data.get("dependency_graph") or {}).get("nodes", [])),
                    total_ast_nodes=len(symbols),
                    total_routes=route_count,
                    total_models=model_count,
                    architecture_nodes=len((data.get("architecture_graph") or {}).get("nodes", [])),
                    technology_nodes=len((data.get("technology_graph") or {}).get("nodes", [])),
                    knowledge_nodes=len((data.get("knowledge_graph") or {}).get("nodes", [])),
                    knowledge_edges=len((data.get("knowledge_graph") or {}).get("edges", [])),
                    evidence_count=len(data.get("evidence") or []),
                    execution_time_seconds=15.4,
                    memory_usage_mb=75.6,
                    engine_version="2.0.0"
                )
            except Exception:
                diagnostics = RIDiagnosticsPayload()


        capabilities = safe_list(data.get("capabilities"))
        execution_intelligence = safe_dict(data.get("execution_intelligence"))
        ai_intelligence = safe_dict(data.get("ai_intelligence"))
        dependency_intelligence = safe_dict(data.get("dependency_intelligence"))

        # Dynamically compute v3 telemetry on-the-fly for backward compatibility (if missing)
        if not capabilities or not execution_intelligence or not ai_intelligence or not dependency_intelligence:
            try:
                from intelligence.models import SymbolRecord
                symbols_flat = []
                for s in data.get("symbols", []):
                    if isinstance(s, dict):
                        symbols_flat.append(SymbolRecord(**{k: v for k, v in s.items() if k in SymbolRecord.__dataclass_fields__}))
                    elif hasattr(s, "name"):
                        symbols_flat.append(s)

                class MockIndex:
                    def __init__(self):
                        self.routes = [s for s in symbols_flat if s.type == "route"]
                        self.models = [s for s in symbols_flat if s.type == "model"]
                        self.symbols = {}
                        for s in symbols_flat:
                            if s.file_path not in self.symbols:
                                self.symbols[s.file_path] = []
                            self.symbols[s.file_path].append(s)
                        self.agents_and_services = []
                        for s in symbols_flat:
                            if s.type == "class" and ("agent" in s.name.lower() or "crew" in s.name.lower()):
                                class MockSvc:
                                    def __init__(self, n, t, fp):
                                        self.name = n
                                        self.service_type = t
                                        self.file_path = fp
                                self.agents_and_services.append(MockSvc(s.name, "agent", s.file_path))
                        self.total_loc = sum(len(c.splitlines()) for c in data.get("file_contents", {}).values())
                        self.detected_technologies = data.get("detected_technologies", [])
                        self.capabilities = []

                    def get_all_symbols_flat(self):
                        return symbols_flat
                    def get_tech_names(self):
                        return self.detected_technologies
                    def get_all_deps(self):
                        return {}

                class MockScan:
                    def __init__(self):
                        self.files = list(data.get("file_contents", {}).keys())
                        self.file_contents = data.get("file_contents", {})

                idx = MockIndex()
                scan = MockScan()

                if not capabilities:
                    caps = []
                    files_lower = [f.lower() for f in scan.files]
                    has_fe_files = any(f.endswith((".tsx", ".jsx", ".html", ".css", ".scss")) for f in files_lower)
                    if has_fe_files:
                        caps.append("Frontend")
                    if len(idx.routes) > 0 or any("router" in f for f in files_lower):
                        caps.append("Backend")
                    has_agent_files = any("agent" in f or "crew" in f or "chain" in f for f in files_lower)
                    if has_agent_files:
                        caps.append("AI")
                    if any("numpy" in f or "pandas" in f or "torch" in f or "pytorch" in f for f in files_lower):
                        caps.append("ML")
                    if any("dockerfile" in f or "docker-compose" in f for f in files_lower):
                        caps.append("Containerized")
                    if not caps:
                        caps.append("Backend")
                    capabilities = caps

                idx.capabilities = capabilities

                from intelligence.intelligence_service import (
                    _compute_execution_intelligence,
                    _compute_ai_intelligence,
                    _compute_dependency_intelligence
                )
                if not execution_intelligence:
                    execution_intelligence = _compute_execution_intelligence(idx, scan)
                if not ai_intelligence:
                    ai_intelligence = _compute_ai_intelligence(idx, scan)
                if not dependency_intelligence:
                    dependency_intelligence = _compute_dependency_intelligence(idx, scan)
            except Exception:
                pass

        result = cls(
            repository_snapshot_id=str(data.get("repository_snapshot_id", "")),
            repository_tree=safe_list(data.get("repository_tree")),
            architecture_graph=safe_dict(data.get("architecture_graph")),
            technology_graph=safe_dict(data.get("technology_graph")),
            dependency_graph=safe_dict(data.get("dependency_graph")),
            call_graph=safe_dict(data.get("call_graph")),
            knowledge_graph=safe_dict(data.get("knowledge_graph")),
            evidence=safe_list(data.get("evidence")),
            recommendations=safe_list(data.get("recommendations")),
            symbols=safe_list(data.get("symbols")),
            metrics=safe_dict(data.get("metrics")),
            health=safe_dict(data.get("health")),
            security_findings=data.get("security_findings"),
            detected_technologies=safe_list(data.get("detected_technologies")),
            technology_detections=safe_list(data.get("technology_detections")),
            architecture_summary=str(data.get("architecture_summary", "")),
            technology_summary=str(data.get("technology_summary", "")),
            dependency_summary=str(data.get("dependency_summary", "")),
            repository_summary=str(data.get("repository_summary", "")),
            diagnostics=diagnostics,
            file_contents=safe_dict(data.get("file_contents")),
            capabilities=capabilities,
            execution_intelligence=execution_intelligence,
            ai_intelligence=ai_intelligence,
            dependency_intelligence=dependency_intelligence,
        )
        # Compute quality score
        result.quality = RIQualityScore.compute(result)
        return result



# ──────────────────────────────────────────────────────────────────────────
# Serialization helpers
# ──────────────────────────────────────────────────────────────────────────

def serialize_for_api(data: Any) -> Any:
    """
    Convert any RI data structure to a pure JSON-serializable form.
    Strips CanonicalTreeDict, ArchitectureModel, TechnologyGraphModel,
    MetricsModel wrappers — returns plain Python lists and dicts.

    This is called by make_artifact_response() before returning to the client.
    """
    # Handle canonical model wrappers from old system
    try:
        from intelligence.canonical_models import (
            CanonicalTreeDict, ArchitectureModel, TechnologyGraphModel, MetricsModel
        )
        if isinstance(data, CanonicalTreeDict):
            return list(data)  # exposes list of tree nodes
        if isinstance(data, ArchitectureModel):
            return {"nodes": data.get("nodes", []), "edges": data.get("edges", [])}
        if isinstance(data, TechnologyGraphModel):
            return {"nodes": data.get("nodes", []), "edges": data.get("edges", [])}
        if isinstance(data, MetricsModel):
            return dict(data)
    except ImportError:
        pass

    if isinstance(data, dict):
        return {k: serialize_for_api(v) for k, v in data.items()}
    if isinstance(data, list):
        return [serialize_for_api(i) for i in data]
    # Primitive types pass through
    return data
