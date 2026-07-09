# Repository Intelligence v2 — Task Tracking

## Phase 1 — Repository Scan (Single Normalized Source)
- [x] Create `backend/intelligence/repository_scan.py`
- [x] Modify `intelligence_service.py` to use RepositoryScan

## Phase 2 — Semantic Index (Shared Single-Pass Index)
- [x] Create `backend/intelligence/semantic_index.py`
  - [x] Multi-language dependency parsing (Python, JS, Go, Rust, Java, C#, Docker)
  - [x] AST symbol/import/route/model extraction
  - [x] Aggregate stats (LOC, functions, classes, AST nodes)

## Phase 3 — Engine Rewrites
- [x] 3a: TechnologyDetector with confidence scores in `architecture_engine.py`
- [x] 3b: ArchitectureEngine using AST (not folder names), 16 layers
- [x] 3c: DependencyAnalyzer multi-language in `dependency_graph.py`
- [x] 3d: EvidenceEngine new rules using SemanticIndex
- [x] 3e: KnowledgeGraphBuilder with AST-derived edges

## Phase 4 — Canonical Contract
- [x] Create `backend/intelligence/ri_contract.py`
  - [x] RepositoryIntelligenceResult dataclass (RIResult)
  - [x] DiagnosticsPayload (18 fields)
  - [x] IntelligenceQuality score
  - [x] to_cache_dict() / from_cache_dict()
- [x] Simplify `canonical_models.py` (no more complex wrappers — handled by serialize_for_api)
- [x] Update `intelligence_service.py` to produce RepositoryIntelligenceResult

## Phase 5 — REST API Serialization & Enriched Telemetry
- [x] Update `main.py` make_artifact_response to use serialize_for_api
- [x] Update status endpoint to expose all diagnostic fields
- [x] Add technology_detections, quality, intelligence_quality, diagnostics to ctx dicts (both main and replay eval)
- [x] Enriched `/projects/{id}/history` timeline endpoint with cached metrics

## Phase 6 — Agent Context Pipeline
- [x] Enrich `context_slicer.py` with technology confidence + architecture summaries
- [x] Update `brief_builder.py` with intelligence_quality score
- [x] Fix `evaluation_context.py` to pass technology_detections, quality, diagnostics to RepositoryIntelligenceResult

## Phase 7 — Stage 4 Pipeline Validation
- [x] Modify `pipeline_validator.py` to add Stage 4 check (validate_repository_intelligence_completeness)

## Phase 8 — Automated Contract & Subsystem Integration
- [x] Create `backend/tests/test_ri_contract.py`
- [x] Verified full test suite runs successfully (23/23 tests passed)

## Phase 9 — Interactive Dashboard Refactoring (Front-end Sync)
- [x] Redesigned `TimelinePanel.tsx` with score progression charts and session reloads
- [x] Redesigned `MetricsPanel.tsx` with codebase size details, stacked language graphs, and filters
- [x] Redesigned `KnowledgeGraphPanel.tsx` with a custom physics engine and progressive drill-down
- [x] Redesigned `ArchitectureGraphPanel.tsx` with horizontal sequential layers and directional curves
- [x] Redesigned `TechnologyGraphPanel.tsx` with force-directed category clustering
- [x] Redesigned `DependencyGraphPanel.tsx` with ecosystem branch clusters
- [x] Redesigned `RepositoryTreePanel.tsx` with LOC/Complexity KPIs, security items list, and code code editor preview

## Phase 10 — Cache Invalidation & Verification
- [x] Delete stale analysis cache entries
- [x] Verify fresh analysis run via `scratch/run_ri_test.py` (Stage 4 PASSED)
