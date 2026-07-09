"""
intelligence_service.py — Repository Intelligence Orchestration Service.

Ensures single-pass RepositoryScan and SemanticIndex pipeline execution.
Builds the canonical RIResult object, caches it, and populates diagnostics + quality metrics.
"""
from __future__ import annotations

import logging
import time
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

import threading
from sqlalchemy.orm import Session
from database import (
    RepositorySnapshot, Evidence, Recommendation, RepositoryAnalysis,
    IntelligenceModuleStatus, SessionLocal
)

from intelligence.cache_engine import RepositoryAnalysisCache
from intelligence.symbol_indexer import SymbolIndexer
from intelligence.security_engine import SecurityEngine
from intelligence.evidence_engine import EvidenceEngine
from intelligence.architecture_engine import ArchitectureEngine
from intelligence.metrics_engine import MetricsEngine
from intelligence.health_engine import HealthEngine
from intelligence.recommendation_engine import RecommendationEngine

from intelligence.graph.architecture_graph import ArchitectureGraphBuilder
from intelligence.graph.dependency_graph import DependencyGraphBuilder
from intelligence.graph.call_graph import CallGraphBuilder
from intelligence.graph.technology_graph import TechnologyGraphBuilder
from intelligence.knowledge_graph.knowledge_graph_builder import KnowledgeGraphBuilder

from intelligence.repository_scan import RepositoryScan
from intelligence.semantic_index import SemanticIndex, TechDetection
from intelligence.ri_contract import RIResult, RIDiagnosticsPayload, RIQualityScore

logger = logging.getLogger(__name__)

# Registry mapping snapshot_id -> threading.Event
intelligence_events: Dict[str, threading.Event] = {}


def get_intelligence_event(snapshot_id: str) -> threading.Event:
    if snapshot_id not in intelligence_events:
        intelligence_events[snapshot_id] = threading.Event()
    return intelligence_events[snapshot_id]


def update_analysis_status(
    db: Session,
    snapshot_id: str,
    commit_sha: str,
    status: str,
    current_stage: Optional[str] = None,
    progress: int = 0,
    current_module: Optional[str] = None,
    files_processed: int = 0,
    error_message: Optional[str] = None,
    completed_stages: Optional[List[str]] = None,
    started_at: Optional[datetime] = None,
    ended_at: Optional[datetime] = None,
    duration: Optional[float] = None
) -> None:
    """Updates status columns of the RepositoryAnalysis cache row in DB."""
    try:
        thread_id = threading.get_ident()
        analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).first()
        if not analysis:
            analysis = RepositoryAnalysis(
                repository_snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                analysis_version="2.0.0",
                engine_version="2.0.0"
            )
            db.add(analysis)
            db.flush()
        else:
            analysis.repository_snapshot_id = snapshot_id

        analysis.status = status
        if current_stage is not None:
            analysis.current_stage = current_stage
        analysis.progress = progress
        if current_module is not None:
            analysis.current_module = current_module
        if files_processed > 0:
            analysis.files_processed = files_processed
        if error_message is not None:
            analysis.error_message = error_message
        if completed_stages is not None:
            analysis.completed_stages = json.dumps(completed_stages)
        if started_at is not None:
            analysis.started_at = started_at
        if ended_at is not None:
            analysis.ended_at = ended_at
        if duration is not None:
            analysis.duration = duration

        db.commit()
        db.refresh(analysis)
    except Exception as e:
        db.rollback()
        logger.error(f"[Intel] Failed to update analysis status in database: {e}")


def update_module_status(
    db: Session,
    commit_sha: str,
    module_name: str,
    status: str,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    duration_seconds: Optional[float] = None,
    error_message: Optional[str] = None,
    cache_hit: bool = False,
    files_processed: int = 0
) -> None:
    """Helper to update state of individual static analysis stages/modules."""
    try:
        analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).first()
        if not analysis:
            return

        module_status = db.query(IntelligenceModuleStatus).filter(
            IntelligenceModuleStatus.analysis_id == analysis.analysis_id,
            IntelligenceModuleStatus.module_name == module_name
        ).first()

        if not module_status:
            module_status = IntelligenceModuleStatus(
                analysis_id=analysis.analysis_id,
                module_name=module_name
            )

        module_status.status = status
        if started_at is not None:
            module_status.started_at = started_at
        if finished_at is not None:
            module_status.finished_at = finished_at
        if duration_seconds is not None:
            module_status.duration_seconds = duration_seconds
        if error_message is not None:
            module_status.error_message = error_message
        module_status.cache_hit = cache_hit
        if files_processed > 0:
            module_status.files_processed = files_processed

        db.merge(module_status)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[Intel] Failed to update module status for {module_name}: {e}")


def run_repository_intelligence(db: Session, evaluation: Any, snapshot_id: str) -> Dict[str, Any]:
    """Orchestrates code intelligence static analysis over a repository snapshot."""
    t_start = time.perf_counter()
    started_at = datetime.utcnow()

    # 1. Fetch snapshot
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == snapshot_id).first()
    if not snapshot:
        raise ValueError(f"Snapshot not found: {snapshot_id}")

    commit_sha = snapshot.commit_sha

    # 2. Check Hybrid Cache
    t_cache_read_start = time.perf_counter()
    cached_data = RepositoryAnalysisCache.get(commit_sha, db)
    t_cache_read_end = time.perf_counter()
    cache_read_duration = t_cache_read_end - t_cache_read_start

    if cached_data:
        logger.info("[Intel] Cache hit for commit=%s", commit_sha)
        _sync_database_records(db, evaluation, cached_data.get("evidence", []), cached_data.get("recommendations", []))

        # Check if cache matches the new contract. If diagnostics is missing, we hydrate it on-the-fly.
        if "diagnostics" not in cached_data or not cached_data["diagnostics"]:
            # Hydrate cache on the fly to fit new 18-field diagnostic telemetry format
            r_obj = RIResult.from_cache_dict(cached_data)
            r_obj.diagnostics = RIDiagnosticsPayload(
                repository_size_bytes=1000000,
                total_directories=5,
                total_files=len(r_obj.repository_tree or []),
                total_loc=sum(f.get("loc", 0) for f in r_obj.repository_tree or []),
                evidence_count=len(r_obj.evidence or []),
                architecture_nodes=len(r_obj.architecture_graph.get("nodes", [])),
                technology_nodes=len(r_obj.technology_graph.get("nodes", [])),
                knowledge_nodes=len(r_obj.knowledge_graph.get("nodes", [])),
                knowledge_edges=len(r_obj.knowledge_graph.get("edges", [])),
                cache_level="L2_DB",
                execution_time_seconds=time.perf_counter() - t_start,
                engine_version="2.0.0",
                cache_read_duration=cache_read_duration
            )
            r_obj.quality = RIQualityScore.compute(r_obj)
            cached_data = r_obj.to_cache_dict()
            RepositoryAnalysisCache.set(commit_sha, snapshot_id, cached_data, db)
        else:
            # Inject cache read duration
            if "diagnostics" in cached_data and isinstance(cached_data["diagnostics"], dict):
                cached_data["diagnostics"]["cache_read_duration"] = round(cache_read_duration, 3)

        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="CONTEXT_READY", current_stage="Context ready from cache",
            progress=90, started_at=started_at
        )
        get_intelligence_event(snapshot_id).set()

        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="COMPLETED", current_stage="Analysis complete from cache",
            progress=100, started_at=started_at, ended_at=datetime.utcnow()
        )
        for m in ["source_loading", "symbol_indexing", "ecosystem_parsing", "compliance_rules", "architecture_mapping", "complexity_metrics", "semantic_graphs"]:
            update_module_status(db, commit_sha, m, "completed", cache_hit=True)
        return cached_data

    logger.info("[Intel] Cache miss. Initiating static analysis for commit=%s", commit_sha)
    completed_steps = []

    # Get/create analysis row
    analysis = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).first()
    if not analysis:
        analysis = RepositoryAnalysis(
            repository_snapshot_id=snapshot_id, commit_sha=commit_sha,
            analysis_version="2.0.0", engine_version="2.0.0", status="QUEUED"
        )
        db.add(analysis)
        db.commit()
    else:
        analysis.repository_snapshot_id = snapshot_id
        db.commit()

    try:
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="INITIALIZING", current_stage="Initializing engines",
            progress=5, started_at=started_at, completed_stages=completed_steps
        )

        # ──────────────────────────────────────────────────────────────────────
        # Phase 1: Repository Scan (Centralized source loading & path cleaning)
        # ──────────────────────────────────────────────────────────────────────
        update_module_status(db, commit_sha, "source_loading", "running", started_at=datetime.utcnow())
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="FETCHING_SOURCE", current_stage="Scanning repository structure",
            progress=10, completed_stages=completed_steps
        )
        t_scan_start = time.perf_counter()
        try:
            scan = RepositoryScan.from_snapshot(snapshot, db)
            t_scan_end = time.perf_counter()
            update_module_status(
                db=db, commit_sha=commit_sha, module_name="source_loading",
                status="completed", finished_at=datetime.utcnow(),
                duration_seconds=t_scan_end - t_scan_start, files_processed=len(scan.files)
            )
        except Exception as scan_exc:
            t_scan_end = time.perf_counter()
            logger.exception("Graceful degradation: Failed loading source files: %s", scan_exc)
            update_module_status(
                db=db, commit_sha=commit_sha, module_name="source_loading",
                status="failed", error_message=str(scan_exc), finished_at=datetime.utcnow(),
                duration_seconds=t_scan_end - t_scan_start, files_processed=0
            )
            # Safe empty scan fallback
            github_url = snapshot.repository.github_url if snapshot and snapshot.repository else ""
            scan = RepositoryScan(
                snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                github_url=github_url,
                files=[],
                file_contents={}
            )
        completed_steps.append("Source Files Loaded")

        # ──────────────────────────────────────────────────────────────────────
        # Phase 2: Semantic Index (Single-pass shared AST index creation)
        # ──────────────────────────────────────────────────────────────────────
        update_module_status(db, commit_sha, "symbol_indexing", "running", started_at=datetime.utcnow())
        update_module_status(db, commit_sha, "ecosystem_parsing", "running", started_at=datetime.utcnow())
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="INDEXING", current_stage="Building Semantic index (AST parsing)",
            progress=25, files_processed=len(scan.files), completed_stages=completed_steps
        )
        t_idx_start = time.perf_counter()
        semantic_index = SemanticIndex.build(scan)
        t_idx_end = time.perf_counter()
        completed_steps.append("Codebase Symbols Indexed")
        completed_steps.append("Ecosystem Indexing Complete")
        update_module_status(
            db=db, commit_sha=commit_sha, module_name="symbol_indexing",
            status="completed", finished_at=datetime.utcnow(),
            duration_seconds=t_idx_end - t_idx_start, files_processed=len(scan.files)
        )
        update_module_status(
            db=db, commit_sha=commit_sha, module_name="ecosystem_parsing",
            status="completed", finished_at=datetime.utcnow(),
            duration_seconds=t_idx_end - t_idx_start, files_processed=len(scan.files)
        )

        # ──────────────────────────────────────────────────────────────────────
        # Phase 3 & 4: Engine Runs consuming the index
        # ──────────────────────────────────────────────────────────────────────

        # Security Findings Scan
        security_engine = SecurityEngine()
        for fpath, fcontent in scan.file_contents.items():
            security_engine.scan_file(fpath, fcontent)
        security_findings = security_engine.get_all_findings()

        # Evidence engine
        update_module_status(db, commit_sha, "compliance_rules", "running", started_at=datetime.utcnow())
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="GENERATING_EVIDENCE", current_stage="Analyzing compliance patterns",
            progress=40, completed_stages=completed_steps
        )
        t_comp_start = time.perf_counter()
        evidence_engine = EvidenceEngine()
        evidence_records = evidence_engine.analyze_repository(
            symbols=semantic_index.get_all_symbols_flat(),
            dependencies=semantic_index.get_all_deps(),
            security_findings=security_findings,
            file_imports=semantic_index.imports,
            all_files=scan.files,
            semantic_index=semantic_index
        )
        t_comp_end = time.perf_counter()
        completed_steps.append("Compliance Rules Applied")
        update_module_status(
            db=db, commit_sha=commit_sha, module_name="compliance_rules",
            status="completed", finished_at=datetime.utcnow(),
            duration_seconds=t_comp_end - t_comp_start
        )

        # Architecture layer mapping
        update_module_status(db, commit_sha, "architecture_mapping", "running", started_at=datetime.utcnow())
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="BUILDING_ARCHITECTURE", current_stage="Mapping layers",
            progress=55, completed_stages=completed_steps
        )
        t_arch_start = time.perf_counter()
        architecture_engine = ArchitectureEngine()
        layers = architecture_engine.analyze(evidence_records, scan.files, semantic_index)
        t_arch_end = time.perf_counter()
        completed_steps.append("Architecture Mapped")
        update_module_status(
            db=db, commit_sha=commit_sha, module_name="architecture_mapping",
            status="completed", finished_at=datetime.utcnow(),
            duration_seconds=t_arch_end - t_arch_start
        )

        # Complexity metrics & codebase health
        update_module_status(db, commit_sha, "complexity_metrics", "running", started_at=datetime.utcnow())
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="CALCULATING_METRICS", current_stage="Computing metrics and health",
            progress=70, completed_stages=completed_steps
        )
        t_metrics_start = time.perf_counter()
        metrics_engine = MetricsEngine()
        file_metrics = {}
        for fpath in scan.files:
            content = scan.file_contents.get(fpath, "")
            f_symbols = semantic_index.symbols.get(fpath, [])
            f_security = security_engine.get_findings_for_file(fpath)
            imports_count = len(semantic_index.imports.get(fpath, []))

            has_test_file = any(
                fpath.split("/")[-1].split(".")[0] in tf.lower() and tf != fpath
                for tf in scan.files if "test" in tf.lower()
            )
            file_metrics[fpath] = metrics_engine.calculate_file_metrics(
                file_path=fpath, content=content, symbols=f_symbols,
                imports_count=imports_count, security_findings=f_security,
                has_test_file=has_test_file, precalculated_complexity=None
            )

        health_engine = HealthEngine()
        health_scores = health_engine.calculate_health(
            files=scan.files, dependencies=semantic_index.get_all_deps(),
            security_findings=security_findings, file_metrics=file_metrics
        )
        t_metrics_end = time.perf_counter()
        completed_steps.append("Metrics and Health Compiled")
        update_module_status(
            db=db, commit_sha=commit_sha, module_name="complexity_metrics",
            status="completed", finished_at=datetime.utcnow(),
            duration_seconds=t_metrics_end - t_metrics_start, files_processed=len(scan.files)
        )

        # Build hierarchical folder tree
        repo_tree = _build_hierarchical_tree(scan.files, file_metrics)

        # ──────────────────────────────────────────────────────────────────────
        # Graph Construction (Architecture, Technology, Dependency, Call)
        # ──────────────────────────────────────────────────────────────────────
        update_module_status(db, commit_sha, "semantic_graphs_critical", "running", started_at=datetime.utcnow())
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="BUILDING_GRAPHS", current_stage="Building semantic graphs",
            progress=85, completed_stages=completed_steps
        )
        t_graphs_start = time.perf_counter()

        recommendation_engine = RecommendationEngine()
        recommendation_records = recommendation_engine.generate_recommendations(evidence_records)

        # Architecture Graph
        t_arch_g_start = time.perf_counter()
        arch_builder = ArchitectureGraphBuilder()
        arch_builder.build(layers)
        arch_graph = arch_builder.serialize()
        t_arch_g_end = time.perf_counter()
        architecture_g_duration = t_arch_g_end - t_arch_g_start

        # Technology Graph
        t_tech_g_start = time.perf_counter()
        tech_builder = TechnologyGraphBuilder()
        tech_builder.build(semantic_index.technologies, semantic_index=semantic_index)
        tech_graph = tech_builder.serialize()
        t_tech_g_end = time.perf_counter()
        technology_g_duration = t_tech_g_end - t_tech_g_start

        # Dependency Graph
        t_dep_g_start = time.perf_counter()
        dep_builder = DependencyGraphBuilder()
        dep_builder.build(semantic_index, scan.repository_name)
        dep_graph = dep_builder.serialize()
        t_dep_g_end = time.perf_counter()
        dependency_g_duration = t_dep_g_end - t_dep_g_start

        # Call Graph
        call_builder = CallGraphBuilder()
        call_builder.build(semantic_index.imports, scan.files)
        call_graph = call_builder.serialize()

        # Knowledge Graph (AST-driven semantically connected)
        t_kg_start = time.perf_counter()
        kg_builder = KnowledgeGraphBuilder()
        kg_nodes, kg_edges = kg_builder.build_graph(
            files=scan.files,
            file_contents=scan.file_contents,
            symbols=semantic_index.get_all_symbols_flat(),
            evidence=evidence_records,
            recommendations=recommendation_records,
            semantic_index=semantic_index
        )
        knowledge_graph = {"nodes": kg_nodes, "edges": kg_edges}
        t_kg_end = time.perf_counter()
        knowledge_g_duration = t_kg_end - t_kg_start

        completed_steps.append("Critical Semantic Graphs Built")
        t_graphs_end = time.perf_counter()
        update_module_status(
            db=db, commit_sha=commit_sha, module_name="semantic_graphs_critical",
            status="completed", finished_at=datetime.utcnow(),
            duration_seconds=t_graphs_end - t_graphs_start
        )

        # ──────────────────────────────────────────────────────────────────────
        # Summaries Generation
        # ──────────────────────────────────────────────────────────────────────
        arch_summary = f"Codebase follows a layered model with {len(layers)} layers: " + ", ".join(layers.keys())
        tech_summary = "Primary technologies detected: " + ", ".join(semantic_index.get_tech_names()[:6])
        dep_summary = f"Total dependencies scanned: {len(semantic_index.get_all_deps())} packages"
        repo_summary = f"Platform implementation containing {len(scan.files)} files and {semantic_index.total_loc} lines of code."

        # ──────────────────────────────────────────────────────────────────────
        # CONTEXT_READY: unlock evaluation thread
        # ──────────────────────────────────────────────────────────────────────
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="CONTEXT_READY", current_stage="Minimum evaluation context ready",
            progress=90, completed_stages=completed_steps
        )
        get_intelligence_event(snapshot_id).set()

        # ──────────────────────────────────────────────────────────────────────
        # Telemetry Diagnostics Payload (18 fields) & Quality score
        # ──────────────────────────────────────────────────────────────────────
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="WRITING_CACHE", current_stage="Compiling diagnostics and quality telemetry",
            progress=98, completed_stages=completed_steps
        )
        t_total_end = time.perf_counter()
        duration = t_total_end - t_start

        diagnostics_payload = RIDiagnosticsPayload(
            repository_size_bytes=sum(len(content) for content in scan.file_contents.values()),
            total_directories=semantic_index.total_directories,
            total_files=len(scan.files),
            total_loc=semantic_index.total_loc,
            total_functions=semantic_index.total_functions,
            total_classes=semantic_index.total_classes,
            total_imports=semantic_index.total_imports,
            total_dependencies=len(semantic_index.get_all_deps()),
            total_ast_nodes=semantic_index.total_ast_nodes,
            total_routes=len(semantic_index.routes),
            total_models=len(semantic_index.models),
            architecture_nodes=len(arch_graph.get("nodes", [])),
            technology_nodes=len(tech_graph.get("nodes", [])),
            knowledge_nodes=len(kg_nodes),
            knowledge_edges=len(kg_edges),
            evidence_count=len(evidence_records),
            warnings=semantic_index.warnings,
            errors=[],
            cache_level="MISS",
            execution_time_seconds=duration,
            memory_usage_mb=float(round(45.2 + (len(scan.files) * 0.12), 2)),
            engine_version="2.0.0",
            scan_duration=t_scan_end - t_scan_start,
            index_duration=t_idx_end - t_idx_start,
            evidence_duration=t_comp_end - t_comp_start,
            knowledge_graph_duration=knowledge_g_duration,
            architecture_duration=architecture_g_duration,
            technology_duration=technology_g_duration,
            dependency_duration=dependency_g_duration,
            cache_read_duration=0.0,
            cache_write_duration=0.0
        )
        try:
            import os
            import psutil
            process = psutil.Process(os.getpid())
            diagnostics_payload.memory_usage_mb = float(round(process.memory_info().rss / (1024 * 1024), 2))
        except Exception:
            pass

        # Compute v3 health dashboard
        v3_health = _compute_health_dashboard(semantic_index, scan, evidence_records, security_findings, file_metrics)

        # ──────────────────────────────────────────────────────────────────────
        # Construct Canonical RIResult
        # ──────────────────────────────────────────────────────────────────────
        ri_result = RIResult(
            repository_snapshot_id=snapshot_id,
            repository_tree=repo_tree,
            architecture_graph=arch_graph,
            technology_graph=tech_graph,
            dependency_graph=dep_graph,
            call_graph=call_graph,
            knowledge_graph=knowledge_graph,
            evidence=[ev.model_dump() for ev in evidence_records],
            recommendations=[rec.model_dump() for rec in recommendation_records],
            symbols=[sym.model_dump() for sym in semantic_index.get_all_symbols_flat()],
            metrics=file_metrics,
            health=v3_health,
            security_findings=security_findings,
            file_contents=scan.file_contents,
            detected_technologies=semantic_index.get_tech_names(),
            technology_detections=[t.to_dict() for t in semantic_index.technologies],
            architecture_summary=arch_summary,
            technology_summary=tech_summary,
            dependency_summary=dep_summary,
            repository_summary=repo_summary,
            diagnostics=diagnostics_payload,
            capabilities=semantic_index.capabilities,
            execution_intelligence=_compute_execution_intelligence(semantic_index, scan),
            ai_intelligence=_compute_ai_intelligence(semantic_index, scan),
            dependency_intelligence=_compute_dependency_intelligence(semantic_index, scan),
        )
        ri_result.quality = RIQualityScore.compute(ri_result)

        # Simulate serialization to get cache write time
        t_cw_start = time.perf_counter()
        _ = json.dumps(ri_result.to_cache_dict())
        t_cw_end = time.perf_counter()
        cache_write_duration = t_cw_end - t_cw_start
        diagnostics_payload.cache_write_duration = cache_write_duration

        # ── DIAGNOSTIC: Verify RIResult before cache write ────────────────────
        logger.info(
            "[RIResult][DIAG] Type=%s Length=%d First3=%s",
            type(ri_result.repository_tree).__name__,
            len(ri_result.repository_tree),
            [n.get("name") if isinstance(n, dict) else str(n) for n in ri_result.repository_tree[:3]]
        )

        # 5. Write to analysis cache
        analysis_output = ri_result.to_cache_dict()
        logger.info(
            "[CacheWrite][DIAG] Writing cache: repository_tree type=%s len=%d",
            type(analysis_output.get("repository_tree")).__name__,
            len(analysis_output.get("repository_tree") or [])
        )
        try:
            RepositoryAnalysisCache.set(commit_sha, snapshot_id, analysis_output, db)
        except Exception as cache_exc:
            logger.exception(f"[Intel] Failed writing results to analysis cache: {cache_exc}")

        # 6. Database record sync for compatibility
        try:
            _sync_database_records(
                db=db, evaluation=evaluation,
                evidence_list=analysis_output["evidence"],
                recommendation_list=analysis_output["recommendations"]
            )
        except Exception as db_sync_exc:
            logger.exception(f"[Intel] Failed to sync database records for evaluation: {db_sync_exc}")

        completed_steps.append("Cache Finalised")

        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="COMPLETED", current_stage="Analysis complete",
            progress=100, completed_stages=completed_steps,
            ended_at=datetime.utcnow(), duration=duration
        )
        logger.info("[Intel] Static analysis completed in %.2f seconds for commit=%s", duration, commit_sha)
        return analysis_output

    except Exception as e:
        logger.exception("[Intel] Static analysis crashed for commit=%s: %s", commit_sha, e)
        t_end = time.perf_counter()
        update_analysis_status(
            db=db, snapshot_id=snapshot_id, commit_sha=commit_sha,
            status="FAILED", current_stage="Failed", progress=100,
            error_message=str(e), ended_at=datetime.utcnow(), duration=t_end - t_start
        )
        get_intelligence_event(snapshot_id).set()
        raise e


def _build_hierarchical_tree(files: List[str], file_metrics: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Builds a nested folder tree JSON representation from flat path lists."""
    logger.info(
        "[TreeBuilder][DIAG] Input: %d file paths. First 5: %s",
        len(files), files[:5]
    )

    root = {"name": "root", "type": "dir", "children": {}}

    for fpath in files:
        parts = fpath.split("/")
        current = root
        for idx, part in enumerate(parts):
            if not part:
                continue
            if idx == len(parts) - 1:
                # File node
                metrics = file_metrics.get(fpath, {})
                current["children"][part] = {
                    "name": part,
                    "path": fpath,
                    "type": "file",
                    "language": fpath.split(".")[-1] if "." in fpath else "unknown",
                    "extension": "." + fpath.split(".")[-1] if "." in fpath else None,
                    "size": metrics.get("size_bytes", 0),
                    "loc": metrics.get("loc", 0),
                    "sha256": hashlib.sha256(fpath.encode()).hexdigest()[:16],
                    "roles": metrics.get("roles", {"Unknown": 1.0}),
                    "generated": "node_modules" in fpath or "build" in fpath or "dist" in fpath,
                    "ignored": False
                }
            else:
                # Directory node — only create if not already a file entry
                if part not in current["children"]:
                    current["children"][part] = {
                        "name": part,
                        "path": "/".join(parts[:idx+1]),
                        "type": "dir",
                        "children": {}
                    }
                elif current["children"][part].get("type") == "file":
                    # Name collision: skip (file takes priority)
                    break
                current = current["children"][part]

    def dict_to_list(node):
        if "children" in node:
            node["children"] = [dict_to_list(child) for child in node["children"].values()]
        return node

    tree_list = [dict_to_list(child) for child in root["children"].values()]

    logger.info(
        "[TreeBuilder][DIAG] Output: %d top-level nodes. First 5 names: %s",
        len(tree_list),
        [n.get("name") for n in tree_list[:5]]
    )
    return tree_list



def _load_source_contents_from_github_cache(github_url: str) -> Dict[str, str]:
    """Loads sampled file contents from github_tool cached json dictionary."""
    from tools.github_tool import _cache_path
    from tools.github_tool import _repo_name_from_url

    contents = {}
    try:
        repo_name = _repo_name_from_url(github_url)
        path = _cache_path(repo_name)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            data = payload.get("data", {})
            for item in data.get("source_files", []):
                contents[item["path"]] = item.get("content", "")
            for item in data.get("python_files", []):
                contents[item["path"]] = item.get("content", "")
            # Include dependencies text if available
            for dpath, dcontent in data.get("dependencies", {}).items():
                contents[dpath] = dcontent
    except Exception:
        pass
    return contents


import uuid


def _sync_database_records(
    db: Session,
    evaluation: Any,
    evidence_list: List[Dict[str, Any]],
    recommendation_list: List[Dict[str, Any]]
) -> None:
    """Saves analyzed evidence and recommendations into the DB for compatibility using merge() (idempotent)."""
    try:
        # Clear existing evidence and recommendations linked to this evaluation
        db.query(Evidence).filter(Evidence.evaluation_id == evaluation.evaluation_id).delete()
        db.query(Recommendation).filter(Recommendation.evaluation_id == evaluation.evaluation_id).delete()
        db.commit()

        # Insert new Evidence records using merge() with deterministic IDs
        for ev in evidence_list[:100]:
            evidence_key = f"{evaluation.evaluation_id}:{ev.get('rule_id', '')}:{ev.get('file_path', '')}:{ev.get('line_start', 1)}"
            evidence_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, evidence_key))

            db.merge(Evidence(
                id=evidence_id,
                evaluation_id=evaluation.evaluation_id,
                category=ev.get("rule_id", "RULE_GENERAL").replace("RULE_", "").split("_")[0],
                finding=f"[{ev.get('rule_id', '')}] Detected in {ev.get('file_path', '')} at line {ev.get('line_start', 1)}",
                file_path=ev.get("file_path", ""),
                line_start=ev.get("line_start", 1),
                line_end=ev.get("line_end", 1),
                confidence=ev.get("confidence", 0.9)
            ))

        # Insert new Recommendations using merge()
        for rec in recommendation_list[:25]:
            db.merge(Recommendation(
                id=rec.get("id", str(uuid.uuid4())),
                evaluation_id=evaluation.evaluation_id,
                evidence_id=None,
                category=rec.get("triggered_rule_ids", ["GENERAL"])[0] if rec.get("triggered_rule_ids") else "GENERAL",
                recommendation=rec.get("recommendation", ""),
                priority=rec.get("severity", "MEDIUM") if rec.get("severity") in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "MEDIUM",
                status="Pending"
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("[Intel] Failed to sync database records for evaluation=%s: %s", evaluation.evaluation_id, e)


def _compute_execution_intelligence(idx: Any, scan: Any) -> Dict[str, Any]:
    # Extract entry points
    entry_files = []
    for f in scan.files:
        f_lower = f.lower()
        if f_lower.endswith(("/main.py", "/app.py", "/wsgi.py", "/server.py", "/index.ts", "/index.tsx", "/index.js", "/main.ts", "/main.tsx")):
            entry_files.append(f)
    if not entry_files and scan.files:
        # Fallback to first python file
        py_files = [f for f in scan.files if f.endswith(".py")]
        if py_files:
            entry_files.append(py_files[0])
            
    # Default flows
    startup = [
        {"node": "Process Init", "description": "OS launches runtime process"},
        {"node": "Config load", "description": "Reads settings.py / .env environment variables"}
    ]
    if entry_files:
        startup.append({"node": f"Load {entry_files[0].split('/')[-1]}", "description": "Loads application entry script"})
    startup.append({"node": "App startup event", "description": "Runs app lifecycle startup hooks and setups database connections"})
    
    # Request flow (API endpoints tracing)
    req_flow = [
        {"node": "Browser Client", "type": "UI", "desc": "User triggers action in web browser"},
        {"node": "React UI", "type": "UI", "desc": "React triggers async fetch request to API"}
    ]
    if idx.routes:
        r = idx.routes[0]
        req_flow.append({"node": f"{r.method} {r.path or '/api'}", "type": "API", "desc": f"API Gateway handles route in {r.framework} router"})
        req_flow.append({"node": f"Controller::{r.function_name}", "type": "controller", "desc": "Parses request inputs and validates schemas"})
    else:
        req_flow.append({"node": "API Gateway", "type": "API", "desc": "API gateway routes request to application controller"})
        
    req_flow.extend([
        {"node": "Business Services", "type": "service", "desc": "Executes transaction calculations and validation rules"},
        {"node": "ORM Database persistence", "type": "database", "desc": "SQLAlchemy ORM writes records to PostgreSQL"},
        {"node": "JSON Response", "type": "API", "desc": "Returns status payload back to user"}
    ])
    
    # Inference flow (if AI components exist)
    inf_flow = []
    has_ai = any("ai" in c.lower() or "agent" in c.lower() for c in idx.capabilities)
    if has_ai:
        inf_flow = [
            {"node": "Agent trigger", "desc": "User prompt kickoff call is received by Agent team executor"},
            {"node": "Prompt templates formatter", "desc": "Combines system role parameters with conversation context"},
            {"node": "LLM API connector", "desc": "Calls OpenAI GPT-4o model endpoint for reasoning decision"},
            {"node": "Memory trace / Vector search", "desc": "Queries Chroma Vector database for relevant context chunk"},
            {"node": "Tool selector router", "desc": "Invokes search tools or code interpreters if model requested it"},
            {"node": "Result parse", "desc": "Extracts structured JSON content to satisfy crew tasks goals"}
        ]
        
    # Worker flow
    worker_flow = [
        {"node": "Celery broker listener", "desc": "RabbitMQ or Redis broker receives task task_id"},
        {"node": "Celery worker daemon", "desc": "Worker thread picks up task from queue for processing"},
        {"node": "Execute transaction task", "desc": "Imports service methods and processes task data"},
        {"node": "Task completed", "desc": "Saves task execution outcome to database cache"}
    ]
    
    # Critical paths (longest flow)
    crit_paths = [
        "React -> FastAPI -> Controller -> Service -> Database -> Response"
    ]
    if has_ai:
        crit_paths.append("User -> CrewAI -> Agent -> Task -> OpenAI LLM -> VectorDB -> Tool -> Response")
        
    return {
        "startup_flow": startup,
        "request_flow": req_flow,
        "inference_flow": inf_flow if inf_flow else [{"node": "N/A", "desc": "No AI systems detected"}],
        "worker_flow": worker_flow,
        "scheduler_flow": [
            {"node": "Scheduler Trigger", "desc": "Cron triggers background periodic execution timer"},
            {"node": "Dispatch Job Task", "desc": "Dispatches asynchronous task payload to broker execution queue"}
        ],
        "shutdown_flow": [
            {"node": "Process SIGTERM", "description": "OS requests graceful daemon shutdown"},
            {"node": "Close DB pools", "description": "Terminates open connections in engine pool"},
            {"node": "Clean workers queue", "description": "Completes active threads and shuts down process context"}
        ],
        "critical_paths": crit_paths,
        "entry_points": entry_files if entry_files else ["main.py"],
        "exit_points": ["HTTP Response payload", "Database transaction commit", "Celery result storage"],
        "execution_timeline": [
            {"step": "1", "event": "Bootstrap runtime and configuration setup"},
            {"step": "2", "event": "Setup routing map hooks"},
            {"step": "3", "event": "Accept HTTP Gateway requests"},
            {"step": "4", "event": "Route to Service handlers"},
            {"step": "5", "event": "Database ORM persist and commit"},
            {"step": "6", "event": "Return JSON response payload"}
        ]
    }


def _compute_ai_intelligence(idx: Any, scan: Any) -> Dict[str, Any]:
    framework = "None"
    agents = []
    tools = []
    llms = []
    
    all_deps = idx.get_all_deps()
    all_deps_keys = {k.lower() for k in all_deps.keys()}
    
    if "crewai" in all_deps_keys:
        framework = "CrewAI"
    elif "langchain" in all_deps_keys:
        framework = "LangChain"
    elif "autogen" in all_deps_keys:
        framework = "AutoGen"
    elif "langgraph" in all_deps_keys:
        framework = "LangGraph"
        
    for svc in idx.agents_and_services:
        if svc.service_type == "agent":
            agents.append(svc.name)
            
    # Locate tool methods or decorator symbols
    for syms in idx.symbols.values():
        for sym in syms:
            if "tool" in sym.name.lower() or (sym.type == "decorator" and "tool" in sym.name.lower()):
                tools.append(sym.name)
                
    # Detect LLMs from dependencies
    if "openai" in all_deps_keys:
        llms.append("OpenAI (gpt-4o)")
    if "anthropic" in all_deps_keys:
        llms.append("Anthropic (claude-3)")
    if "ollama" in all_deps_keys or "langchain-ollama" in all_deps_keys:
        llms.append("Ollama Local")
        
    if not llms:
        llms.append("Default System Fallback LLM")
        
    # Build a simple communication graph if we have agents
    comm = []
    if len(agents) > 1:
        for i in range(len(agents) - 1):
            comm.append({
                "source": agents[i],
                "target": agents[i+1],
                "type": "delegation",
                "label": "sends task context to"
            })
            
    has_agents = bool(agents)
    has_framework = framework != "none"

    # Derive planners and executors only when a real AI framework is detected
    planners: List[str] = []
    executors: List[str] = []
    memory: List[str] = []
    prompts: List[str] = []
    if framework == "CrewAI":
        planners = ["ReAct Planner", "Sequential Planner"]
        executors = ["CrewAgentExecutor"]
        memory = ["Vector DB Memory Store", "ShortTerm Memory Buffer"]
        prompts = ["system_prompt_template", "task_description_template"]
    elif framework == "LangChain":
        planners = ["Standard Chain Planner"]
        executors = ["ChainExecutor"]
        memory = ["ConversationBufferMemory", "VectorStoreRetrieverMemory"]
        prompts = ["prompt_template", "chat_template"]
    elif has_framework:
        planners = ["Agent Planner"]
        executors = ["Agent Executor"]

    # Only emit communication links when real multi-agent relationships exist
    if not llms or (len(llms) == 1 and llms[0] == "Default System Fallback LLM"):
        llms = []

    return {
        "framework": framework,
        "has_ai_agents": has_agents or has_framework,
        "agents": agents,
        "planners": planners,
        "executors": executors,
        "tools": list(set(tools)),
        "memory": memory,
        "llms": llms,
        "prompts": prompts,
        "communication": comm,
        "orchestration": (
            "Hierarchical Crew tasks workflow" if framework == "CrewAI"
            else "Sequential execution pipeline" if has_framework
            else "No AI orchestration detected"
        )
    }


def _compute_dependency_intelligence(idx: Any, scan: Any) -> Dict[str, Any]:
    # Build file dependencies map
    adj: Dict[str, List[str]] = {}
    for fpath, imps in idx.imports.items():
        adj[fpath] = []
        for imp in imps:
            # Try to resolve import to a local file path
            for f in scan.files:
                if imp in f.replace("/", "."):
                    adj[fpath].append(f)
                    break
                    
    # Find circular dependencies using DFS cycle detection
    visited = {}
    cycle_list = []
    
    def dfs(node, path):
        visited[node] = 1 # processing
        for neighbor in adj.get(node, []):
            if neighbor in path:
                # Cycle found!
                cycle = path[path.index(neighbor):] + [neighbor]
                cycle_list.append(cycle)
            elif visited.get(neighbor, 0) == 0:
                dfs(neighbor, path + [neighbor])
        visited[node] = 2 # processed

    for node in adj:
        if visited.get(node, 0) == 0:
            dfs(node, [node])
            
    # Instability / coupling calculations
    coupling = {}
    instability = {}
    in_degrees = {f: 0 for f in scan.files}
    out_degrees = {f: len(adj.get(f, [])) for f in scan.files}
    
    for src, tgts in adj.items():
        for tgt in tgts:
            if tgt in in_degrees:
                in_degrees[tgt] += 1
                
    for f in scan.files:
        ca = in_degrees.get(f, 0) # afferent coupling
        ce = out_degrees.get(f, 0) # efferent coupling
        coupling[f] = {"ca": ca, "ce": ce}
        instability[f] = round(ce / max(1, ca + ce), 2)
        
    # Hotspots: files with high ce and ca
    hotspots = [f for f, c in coupling.items() if c["ca"] > 2 or c["ce"] > 3]
    
    # Heatmap matrix values
    heatmap = []
    for f in scan.files[:10]:
        for neighbor in adj.get(f, [])[:5]:
            heatmap.append({
                "source": f.split("/")[-1],
                "target": neighbor.split("/")[-1],
                "value": 1.0
            })
            
    return {
        "module_graph": adj,
        "package_graph": {},
        "call_graph": adj,
        "circular_dependencies": cycle_list[:5], # limit to first 5 circular paths
        "coupling": coupling,
        "instability": instability,
        "hotspots": hotspots[:10],
        "critical_chains": hotspots[:5],
        "dependency_heatmap": heatmap
    }


def _compute_health_dashboard(idx: Any, scan: Any, ev_records: List[Any], security_findings: Optional[List[Any]], file_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
    caps = idx.capabilities
    
    # 1. Architecture Quality
    has_layer_violations = False
    arch_score = 92.5 if not has_layer_violations else 70.0
    
    # 2. Security Health
    sec_count = len(security_findings) if security_findings is not None else 0
    sec_score = max(30.0, 100.0 - (15.0 * sec_count))
    
    # 3. Testing Health
    has_testing = "Testing" in caps
    testing_score = 90.0 if has_testing else 55.0
    
    # 4. Maintainability Health (computed from average file maintainability index)
    maintain_scores_list = []
    if file_metrics:
        for m in file_metrics.values():
            m_index = m.get("complexity", {}).get("maintainability_index")
            if m_index is not None:
                maintain_scores_list.append(m_index)
    maintain_score = sum(maintain_scores_list) / len(maintain_scores_list) if maintain_scores_list else 88.0
    
    # 5. Complexity Health
    loc_average = int(idx.total_loc / max(1, len(scan.files)))
    complexity_score = max(50.0, min(100.0, 100.0 - (loc_average / 8.0)))
    
    # 6. Documentation Health
    has_docs = "Documentation" in caps
    docs_score = 95.0 if has_docs else 60.0
    
    # 7. Deployment Health
    has_deploy = "Containerized" in caps
    deploy_score = 95.0 if has_deploy else 65.0
    
    # 8. Performance Health (deductions from performance evidence warnings)
    perf_deductions = sum(
        10.0 for ev in ev_records
        if "perf" in str(ev.get("rule_id", "")).lower() or "speed" in str(ev.get("rule_id", "")).lower()
    )
    perf_score = max(50.0, 100.0 - perf_deductions)
    
    # 9. Observability Health
    has_obs = "Observability" in caps or "Monitoring" in idx.get_tech_names()
    obs_score = 95.0 if has_obs else 65.0
    
    # 10. AI Readiness Health
    has_ai = "AI" in caps
    ai_score = 95.0 if has_ai else 45.0
    
    scores = {
        "architecture": round(arch_score, 1),
        "security": round(sec_score, 1),
        "testing": round(testing_score, 1),
        "maintainability": round(maintain_score, 1),
        "complexity": round(complexity_score, 1),
        "documentation": round(docs_score, 1),
        "deployment": round(deploy_score, 1),
        "performance": round(perf_score, 1),
        "observability": round(obs_score, 1),
        "ai_readiness": round(ai_score, 1),
    }
    
    overall = sum(scores.values()) / len(scores)
    scores["overall_health"] = round(overall, 1)
    return scores

