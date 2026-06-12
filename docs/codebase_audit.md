# YOWON AI Codebase Audit

## Architecture Overview

YOWON AI is a React/Vite client backed by FastAPI, SQLAlchemy/SQLite, CrewAI-compatible
Ollama agents, ChromaDB context storage, GitHub/PDF/PPT ingestion, deterministic scoring, and
ReportLab PDF generation.

## Data Flow

1. `POST /upload-project` stores metadata and uploaded file paths.
2. `POST /evaluate/{id}` starts a background evaluation.
3. The parser gathers GitHub, document, and static-security evidence.
4. A deterministic brief and agent-specific slices feed the five-agent Council.
5. Pydantic validates or conservatively replaces malformed agent JSON.
6. The score engine applies the selected rubric, evidence penalties, calibration, and confidence.
7. Insight summarizes the deterministic verdict without changing numeric scores.
8. Evaluations and report metadata are persisted; JSON/PDF reports are served to React.

## Agent Workflow

The coordinator builds a compact evidence brief. Technical, security, innovation, presentation,
and risk specialists run in parallel. The score engine aggregates their results. A narrative agent
produces executive prose from the computed verdict.

## Audit Findings

- The previous global weights summed to `1.20`, inflating ordinary projects into the 90s.
- Prompts used production-readiness anchors for every project, penalizing academic and prototype work.
- Confidence displayed by React was derived from score consensus and overall score, not evidence quality.
- Missing tests, documentation, deployment evidence, and innovation evidence did not consistently reduce scores.
- Project context was absent from persistence, specialist rubrics, reports, and the UI.
- GitHub ingestion samples only five Python files; repository coverage and non-Python security analysis are limited.
- Security dependency checks are heuristic and only inspect a narrow set of dependency files.
- Two parallel context/brief implementations exist under `context/` and `eval_context/`, creating technical debt.
- Several legacy combined-agent modules are not part of the active pipeline and can confuse maintenance.
- Background tasks run inside the API process; restarts can lose in-flight work.
- Uploads are read into memory and lack explicit size/type enforcement in the API.
- SQLite auto-migrations are practical for local use but should move to Alembic for production.
- Generated reports and Chroma data live inside the repository workspace and need lifecycle management.
- Source files contain legacy mojibake characters that should be normalized separately to avoid noisy changes.

## Implemented Remediation

- Added a configuration-driven project-type rubric system with normalized weights.
- Added context-aware prompt instructions and project type to every specialist brief.
- Added strict evidence penalties, exceptional-score gating, calibrated bands, and measurable confidence.
- Added project type persistence and backward-compatible SQLite migration.
- Added evaluation context and score explanation to JSON, PDF, evaluation dashboard, and report UI.
- Added deterministic calibration and benchmark tests.

## Remaining Production Recommendations

- Adopt Alembic migrations and a durable job queue.
- Expand repository ingestion and language-aware security scanners.
- Add API upload limits, authentication, authorization, and retention policies.
- Consolidate duplicate context and legacy agent modules.
- Add integration tests with mocked Ollama/GitHub and end-to-end browser tests.
