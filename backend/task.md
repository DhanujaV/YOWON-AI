# TODO checklist — Software Architecture Intelligence Platform (RI v3)

## Backend Engine & Contract Extensions
- [x] Phase 1: capabilities detection in `semantic_index.py` & capability list in `RIResult`
- [x] Phase 2: upgrade `ArchitectureEngine` for 26 layers & rich properties per component
- [x] Phase 3: trace request flows, startup sequence, and workers to populate `execution_intelligence`
- [x] Phase 4 & 5: AI orchestration tracer in `semantic_index.py` for CrewAI/LangChain, mapping vector DBs, tools, and prompts under `ai_intelligence`
- [x] Phase 6: circular dependencies, module/package coupling, and instability index calculations in `dependency_graph.py` under `dependency_intelligence`
- [x] Phase 7: update `knowledge_graph_builder.py` with hierarchical conceptual levels
- [x] Phase 8 & 9: score health categories (Cohesion, SOLID, Technical Debt) in `health_engine.py` / `metrics_engine.py`
- [x] Phase 10: compile structured JSON `repository_story` on-the-fly from cached facts in `intelligence_service.py`
- [x] Phase 11: implement dynamic Ollama executive summaries in `main.py` route
- [x] Phase 12: define endpoints for cross-linking, dependency tracing, and impact analysis in `main.py`
- [x] Phase 16: update pipeline status steps to support progressive Large Repository execution progress (Quick Scan -> Semantic Scan -> Architecture -> Technology -> Dependencies -> Knowledge -> AI -> Story -> Executive Summary)

## Frontend UI Dashboard Updates
- [x] Phase 13: build `SoftwareArchitectureNavigator.tsx` central view
- [x] Phase 14: connect actual AST diagnostics in `DiagnosticsPanel.tsx` (remove mock values)
- [x] Phase 15: update file inspector details in `RepositoryTreePanel.tsx`
- [x] Phase 17: add zoom, pan, legends, search filters, and PNG/SVG export downloads to all graph components
- [x] Phase 3 & 5 UI: create `ExecutionFlowPanel.tsx` and `AIAgentsPanel.tsx`
- [x] Phase 9 & 10 UI: create `RepositoryStoryPanel.tsx` and `ExecutiveSummaryPanel.tsx`
- [x] Phase 12 UI: bind click events in all panels to highlight connected entities
- [x] Phase 15 UI: timeline evolution support for run comparisons
