"""Context-aware deterministic scoring, evidence gates, and confidence."""

from __future__ import annotations

from statistics import pstdev
from typing import Any

from scoring.rubrics import get_rubric
from validation.schemas import (
    AgentScores, InnovationReport, PresentationReport, RiskReport,
    SecurityReport, TechnicalReport,
)

DIMENSIONS = ("technical", "security", "scalability", "innovation", "presentation", "impact")
GLOBAL_BANDS = (
    (91, "Exceptional"),
    (81, "Excellent"),
    (61, "Strong"),
    (41, "Functional"),
    (21, "Prototype"),
    (0, "Incomplete"),
)
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".cs",
    ".php", ".rb", ".swift", ".kt", ".scala", ".m", ".mm", ".sql", ".ipynb",
}
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".pdf", ".doc", ".docx"}
PRESENTATION_EXTENSIONS = {".ppt", ".pptx", ".key"}
DATA_EXTENSIONS = {".csv", ".tsv", ".jsonl", ".parquet", ".pkl", ".pickle", ".npy", ".npz", ".xlsx", ".xls", ".db", ".sqlite"}
MODEL_ARTIFACT_EXTENSIONS = {".h5", ".pt", ".pth", ".onnx", ".pkl", ".joblib"}
DATASET_EXTENSIONS = {".csv", ".npy", ".parquet", ".json"}
MAX_TOTAL_PENALTY = 45
CONFIG_FILENAMES = {
    "package.json", "requirements.txt", "requirements-dev.txt", "pyproject.toml",
    "pom.xml", "build.gradle", "go.mod", "cargo.toml", "gemfile", "pipfile",
    "tsconfig.json", "vite.config.ts", "docker-compose.yml",
}
DEPLOYMENT_NAMES = {
    "dockerfile", "docker-compose.yml", "vercel.json", "netlify.toml", "render.yaml",
    "procfile", "kubernetes", "k8s", "helm", "terraform", ".github", "deploy",
}
ARCHITECTURE_TERMS = ("architecture", "design", "system design", "component", "module", "service", "api", "schema")
SECURITY_TERMS = ("auth", "jwt", "oauth", "permission", "rbac", "sanitize", "csrf", "cors", "secret", "encrypt", "hash")
IMPACT_TERMS = ("adoption", "user", "customer", "metric", "outcome", "deployed", "pilot", "traction", "revenue", "impact")
BUSINESS_TERMS = ("market", "customer", "revenue", "business model", "pricing", "competitor", "tam", "sam", "som", "traction")
ML_TERMS = ("tensorflow", "torch", "pytorch", "sklearn", "scikit", "keras", "xgboost", "opencv", "nlp", "classifier", "recommendation", "recommender", "machine learning", "deep learning", "model")
API_TERMS = ("fastapi", "flask", "django", "express", "router", "endpoint", "api", "controller")


def _clean_structure_item(item: str) -> str:
    return str(item).replace("ðŸ“", "").replace("ðŸ“„", "").strip()


def _suffix(path: str) -> str:
    name = path.lower().split("/")[-1].strip()
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


def _repository_statistics(ctx: dict[str, Any]) -> dict[str, int]:
    gh = ctx.get("github") or {}
    supplied = gh.get("repository_statistics")
    if isinstance(supplied, dict) and supplied:
        defaults = {
            "total_files": 0, "code_files": 0, "documentation_files": 0,
            "presentation_files": 0, "test_files": 0, "configuration_files": 0,
            "deployment_files": 0, "data_files": 0, "source_modules": 0, "meaningful_files": 0,
            "repository_completeness_score": 0,
        }
        return {key: int(supplied.get(key, defaults[key]) or 0) for key in defaults}

    structure = [_clean_structure_item(x) for x in gh.get("folder_structure") or []]
    files = [x for x in structure if x and "." in x.split("/")[-1]]
    lower = [x.lower() for x in files]
    code_files = [x for x in lower if _suffix(x) in SOURCE_EXTENSIONS]
    docs = [x for x in lower if _suffix(x) in DOC_EXTENSIONS or "readme" in x or "docs" in x]
    presentations = [x for x in lower if _suffix(x) in PRESENTATION_EXTENSIONS]
    tests = [x for x in lower if any(t in x for t in ("test", "spec", "__tests__"))]
    data = [x for x in lower if _suffix(x) in DATA_EXTENSIONS or "/data/" in x or x.startswith("data/")]
    configs = [x for x in lower if x.split("/")[-1] in CONFIG_FILENAMES or _suffix(x) in {".json", ".toml", ".yml", ".yaml", ".ini", ".cfg"}]
    deployments = [x for x in lower if any(term in x for term in DEPLOYMENT_NAMES)]
    modules = {x.split("/")[0] for x in code_files if "/" in x} | {x.rsplit(".", 1)[0] for x in code_files}
    return {
        "total_files": len(files),
        "code_files": len(code_files) or len(gh.get("python_files") or []),
        "documentation_files": len(docs),
        "presentation_files": len(presentations),
        "test_files": len(tests),
        "configuration_files": len(configs) or len(gh.get("dependencies") or {}),
        "deployment_files": len(deployments),
        "data_files": len(data),
        "source_modules": len(modules),
        "meaningful_files": len(set(code_files + docs + presentations + tests + configs + deployments + data)),
    }


def _repository_file_list(ctx: dict[str, Any]) -> list[str]:
    gh = ctx.get("github") or {}
    files = gh.get("repository_files") or []
    if files:
        return [str(item).replace("\\", "/").lower() for item in files]
    return [
        _clean_structure_item(item).replace("\\", "/").lower()
        for item in gh.get("folder_structure") or []
        if "." in str(item).split("/")[-1]
    ]


def _artifact_profile(ctx: dict[str, Any]) -> dict[str, Any]:
    files = _repository_file_list(ctx)
    model_files = [path for path in files if _suffix(path) in MODEL_ARTIFACT_EXTENSIONS]
    dataset_files = [
        path for path in files
        if _suffix(path) in DATASET_EXTENSIONS or "/data/" in path or path.startswith("data/")
    ]
    return {
        "model_files": model_files[:10],
        "dataset_files": dataset_files[:10],
        "has_model_artifact": bool(model_files),
        "has_dataset_artifact": bool(dataset_files),
    }


def _only_readme_or_config(ctx: dict[str, Any], stats: dict[str, int]) -> bool:
    files = _repository_file_list(ctx)
    if not files:
        return False
    readme_files = [f for f in files if f.split("/")[-1].startswith("readme")]
    gitignore_files = [f for f in files if f.split("/")[-1] == ".gitignore"]
    config_like = [
        f for f in files
        if f.split("/")[-1] in CONFIG_FILENAMES
        or _suffix(f) in {".json", ".toml", ".yml", ".yaml", ".ini", ".cfg"}
    ]
    allowed = set(readme_files + gitignore_files + config_like)
    substantive = (
        stats.get("code_files", 0)
        + stats.get("presentation_files", 0)
        + stats.get("test_files", 0)
        + stats.get("deployment_files", 0)
        + stats.get("data_files", 0)
    )
    return substantive == 0 and bool(files) and set(files).issubset(allowed)


def _score_band(score: int) -> str:
    return next(label for threshold, label in GLOBAL_BANDS if score >= threshold)


def _calibrate_curve(raw: int) -> int:
    raw = max(0, min(100, int(raw)))
    anchors = ((0, 0), (40, 40), (60, 55), (75, 65), (85, 72), (95, 80), (100, 94))
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if raw <= x1:
            pct = (raw - x0) / max(1, x1 - x0)
            return round(y0 + pct * (y1 - y0))
    return 88


def build_evidence_profile(ctx: dict[str, Any], parse_sources: dict[str, str] | None = None) -> dict[str, Any]:
    gh, sec = ctx.get("github") or {}, ctx.get("security") or {}
    structure_items = gh.get("folder_structure") or []
    structure = " ".join(structure_items).lower()
    readme = gh.get("readme") or ""
    description = ctx.get("description") or ""
    pdf_text = ((ctx.get("pdf") or {}).get("full_text") or "")
    ppt_text = ((ctx.get("ppt") or {}).get("full_text") or "")
    evidence_text = " ".join((description, readme, pdf_text, ppt_text, structure)).lower()
    dependency_text = " ".join(str(v) for v in (gh.get("dependencies") or {}).values()).lower()
    has_repo = bool(gh and not gh.get("error"))
    stats = _repository_statistics(ctx)
    artifacts = _artifact_profile(ctx)
    code = ctx.get("code_reader") or {}
    architecture = ctx.get("architecture") or {}
    technical_evidence = ctx.get("technical_evidence") or {}
    code_signals = code.get("signals") or {}
    architecture_layers = architecture.get("layers") or {}
    evidence_found = set(technical_evidence.get("evidence_found") or [])
    detected_technologies = technical_evidence.get("detected_technologies") or code.get("frameworks") or []
    detected_algorithms = technical_evidence.get("detected_algorithms") or code.get("algorithms") or []
    has_report_document = bool((pdf_text and len(pdf_text) > 80) or (ppt_text and len(ppt_text) > 80))
    has_documents = bool(
        stats["documentation_files"] or stats["presentation_files"]
        or len(readme) > 80 or (pdf_text and len(pdf_text) > 80) or (ppt_text and len(ppt_text) > 80)
    )
    has_meaningful_text = len(description.strip()) > 80 or has_documents
    repository_has_content = has_repo and bool(
        stats["code_files"] or stats["documentation_files"] or stats["presentation_files"]
        or stats["deployment_files"] or stats.get("data_files", 0)
        or (readme and readme != "[No README found]" and len(readme.strip()) > 80)
    )
    source_code_exists = stats["code_files"] > 0 or bool(gh.get("python_files"))
    architecture_evidence = source_code_exists and (
        stats["source_modules"] >= 2 or any(term in evidence_text for term in ARCHITECTURE_TERMS)
    ) or bool(architecture_layers.get("backend") or architecture_layers.get("frontend") or architecture_layers.get("api_layer"))
    multiple_components = stats["source_modules"] >= 2 or stats["code_files"] >= 3 or sum(bool(v) for v in architecture_layers.values()) >= 2
    security_evidence = bool(sec) and (
        bool(sec.get("bandit_issues") is not None)
        or bool(sec.get("dependency_warnings") is not None)
        or bool(sec.get("summary"))
    )
    no_critical_security = not sec.get("secret_findings") and sec.get("risk_level", "LOW") != "CRITICAL"
    novelty = any(x in evidence_text for x in ("novel", "novelty", "differentiator", "unique", "original", "new approach"))
    ml_evidence = bool(code_signals.get("ml_model")) or artifacts["has_model_artifact"] or any(x in (evidence_text + " " + dependency_text) for x in ML_TERMS)
    api_evidence = bool(code_signals.get("rest_api") or architecture_layers.get("api_layer")) or any(x in (evidence_text + " " + dependency_text) for x in API_TERMS)
    differentiation = any(x in evidence_text for x in ("competitor", "alternative", "different", "differentiation", "vs ", "compared with"))
    outcomes = any(x in evidence_text for x in IMPACT_TERMS)
    adoption = any(x in evidence_text for x in ("users", "customers", "stars", "downloads", "pilot", "adoption", "traction"))

    checks = {
        "source_code": source_code_exists,
        "architecture": architecture_evidence,
        "multiple_components": multiple_components,
        "documentation": bool(len(readme) > 120 or len(pdf_text) > 120 or len(ppt_text) > 120),
        "presentation_material": bool(ctx.get("ppt") or stats["presentation_files"] or len(readme) > 500 or len(pdf_text) > 500),
        "tests": bool(code_signals.get("testing")) or stats["test_files"] > 0 or any(x in structure for x in ("test", "spec", "__tests__")),
        "deployment": bool(code_signals.get("deployment_pattern") or architecture_layers.get("deployment_layer")) or stats["deployment_files"] > 0 or any(x in structure for x in DEPLOYMENT_NAMES),
        "dependency_analysis": security_evidence and (stats["configuration_files"] > 0 or bool(gh.get("dependencies"))),
        "security_practices": bool(code_signals.get("security_implementation") or code_signals.get("authentication")) or (security_evidence and any(x in evidence_text for x in SECURITY_TERMS)),
        "no_critical_findings": no_critical_security,
        "innovation_evidence": bool(detected_algorithms or code_signals.get("custom_algorithm")) or novelty or differentiation or ml_evidence or bool(gh.get("topics")),
        "novelty_evidence": bool(detected_algorithms or code_signals.get("custom_algorithm")) or novelty or ml_evidence,
        "differentiation_evidence": bool(detected_algorithms or code_signals.get("custom_algorithm")) or differentiation or ml_evidence,
        "impact_evidence": outcomes,
        "adoption_evidence": adoption or int(gh.get("stars") or 0) > 0 or int(gh.get("forks") or 0) > 0,
        "real_world_value": outcomes or any(x in evidence_text for x in ("problem", "workflow", "saves", "reduces", "improves")),
        "baseline_comparison": any(x in evidence_text for x in ("baseline", "benchmark", "compared with", "comparison")),
        "experimental_evidence": bool(ml_evidence and (detected_algorithms or artifacts["has_dataset_artifact"])) or artifacts["has_dataset_artifact"] or any(x in evidence_text for x in ("experiment", "results", "accuracy", "precision", "recall", "f1", "dataset", "evaluation")),
        "reproducibility": any(x in evidence_text for x in ("reproduc", "seed", "methodology", "method", "notebook", "environment")),
        "citations": any(x in evidence_text for x in ("references", "citation", "doi", "arxiv", "et al.", "bibliography")),
        "market_evidence": any(x in evidence_text for x in BUSINESS_TERMS),
        "business_model": any(x in evidence_text for x in ("business model", "pricing", "revenue", "subscription", "gtm", "go-to-market")),
        "competitive_analysis": any(x in evidence_text for x in ("competitor", "competitive", "alternative", "market map")),
        "contribution_readiness": any(x in evidence_text for x in ("contributing", "code of conduct", "issue template", "pull request", "license")),
        "ml_evidence": ml_evidence,
        "model_artifact": artifacts["has_model_artifact"],
        "dataset_artifact": artifacts["has_dataset_artifact"],
        "api_evidence": api_evidence,
        "database_evidence": bool(code_signals.get("database") or architecture_layers.get("database") or "Database" in evidence_found),
        "authentication_evidence": bool(code_signals.get("authentication") or architecture_layers.get("authentication") or "Authentication" in evidence_found),
        "custom_algorithm": bool(code_signals.get("custom_algorithm") or "Custom algorithm" in evidence_found),
        "integration_evidence": bool(code_signals.get("integrations") or architecture_layers.get("integrations") or "External integrations" in evidence_found),
        "queue_evidence": bool(code_signals.get("queue") or architecture_layers.get("queues") or "Queue/background jobs" in evidence_found),
        "vector_database_evidence": bool(code_signals.get("vector_database") or architecture_layers.get("vector_databases") or "Vector database" in evidence_found),
        "agent_system_evidence": bool(code_signals.get("agent_system") or architecture_layers.get("agent_systems") or "Agent system" in evidence_found),
    }
    evaluable_files = (
        stats["meaningful_files"]
        + stats["code_files"]
        + stats["documentation_files"]
        + stats["presentation_files"]
        + stats.get("data_files", 0)
    )
    empty_repository = (evaluable_files == 0 and not has_meaningful_text) or _only_readme_or_config(ctx, stats)
    available = sum((repository_has_content, bool(description.strip()), bool(ctx.get("pdf")), bool(ctx.get("ppt")), security_evidence))
    repository_coverage = min(100, stats["repository_completeness_score"] if "repository_completeness_score" in stats else (
        min(35, stats["code_files"] * 6)
        + min(20, stats["documentation_files"] * 10)
        + min(15, stats["test_files"] * 8)
        + min(15, stats["configuration_files"] * 5)
        + min(15, stats["deployment_files"] * 10)
        + min(8, stats.get("data_files", 0) * 4)
        + (8 if artifacts["has_model_artifact"] else 0)
        + (6 if artifacts["has_dataset_artifact"] else 0)
    ))
    completeness_score = min(
        100,
        min(35, stats["code_files"] * 7)
        + min(15, stats["documentation_files"] * 8)
        + min(15, stats["test_files"] * 8)
        + min(10, stats["configuration_files"] * 4)
        + min(10, stats["deployment_files"] * 10)
        + min(8, stats.get("data_files", 0) * 4)
        + (10 if checks["architecture"] else 0)
        + (5 if security_evidence else 0),
    )
    if artifacts["has_model_artifact"]:
        repository_coverage = min(100, repository_coverage + 8)
        completeness_score = min(100, completeness_score + 8)
    if artifacts["has_dataset_artifact"]:
        repository_coverage = min(100, repository_coverage + 6)
        completeness_score = min(100, completeness_score + 6)
    sources = parse_sources or {}
    json_validity = round(100 * sum(v == "llm" for v in sources.values()) / len(sources)) if sources else 100
    return {
        "checks": checks,
        "repository_statistics": {**stats, "repository_completeness_score": completeness_score},
        "artifacts": artifacts,
        "has_repository": has_repo,
        "repository_has_content": repository_has_content,
        "empty_repository": empty_repository,
        "trivial_repository": 0 < stats["meaningful_files"] <= 3 and completeness_score < 35,
        "tiny_repository": 0 < stats["meaningful_files"] <= 8,
        "tiny_incomplete_project": 0 < stats["meaningful_files"] <= 8 and (
            completeness_score < 55
            or not checks["architecture"]
            or not checks["documentation"]
            or not checks["tests"]
        ),
        "small_repository": 9 <= stats["meaningful_files"] <= 15,
        "small_academic_project": 4 <= stats["meaningful_files"] <= 15 and rubric_like_academic(ctx.get("project_type")),
        "complete_project": completeness_score >= 75 and stats["code_files"] >= 4 and checks["documentation"] and checks["tests"],
        "incomplete_project": not checks["source_code"] and not checks["documentation"],
        "has_report_document": has_report_document,
        "data_availability": round(available / 5 * 100),
        "repository_coverage": repository_coverage,
        "repository_completeness_score": completeness_score,
        "confidence_bonus": (8 if artifacts["has_model_artifact"] else 0) + (6 if artifacts["has_dataset_artifact"] else 0),
        "json_validity": json_validity,
        "evidence_quality": _score_band(round((completeness_score + repository_coverage + sum(bool(v) for v in checks.values()) / len(checks) * 100) / 3)),
        "code_reader": code,
        "architecture": architecture,
        "technical_evidence": technical_evidence,
        "submitted_project_type": ctx.get("submitted_project_type", ctx.get("project_type", "")),
        "detected_project_type": ctx.get("detected_project_type", (ctx.get("project_type_detection") or {}).get("project_type", "")),
        "detected_project_confidence": ctx.get("detected_project_confidence", (ctx.get("project_type_detection") or {}).get("confidence", 0)),
        "rest_apis_found": technical_evidence.get("rest_apis_found", []),
        "database_usage": technical_evidence.get("database_usage", []),
        "authentication_usage": technical_evidence.get("authentication_usage", []),
        "integrations": technical_evidence.get("integrations", []),
        "top_code_snippets": technical_evidence.get("top_code_snippets", []),
        "detected_technologies": detected_technologies,
        "detected_algorithms": detected_algorithms,
        "community_impact_score": _community_impact_score(gh),
        "project_type_detection": ctx.get("project_type_detection", {}),
    }


def rubric_like_academic(project_type: str | None) -> bool:
    return str(project_type or "").strip() in {"University Project", "Research Project", "Hackathon Project"}


def build_empty_repository_rejection(ctx: dict[str, Any], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = evidence or build_evidence_profile(ctx)
    zero_scores = {key: 0 for key in DIMENSIONS}
    reason = "Repository contains no evaluable content."
    return {
        "status": "INSUFFICIENT_EVIDENCE",
        "overall_score": 0,
        "readiness": 0,
        "readiness_score": 0,
        "raw_weighted_score": 0,
        "verdict": "REJECT",
        "risk_level": "CRITICAL",
        "agent_scores": zero_scores,
        "raw_agent_scores": zero_scores,
        "calibrated_agent_scores": zero_scores,
        "agent_calibration_reasons": {key: [reason] for key in DIMENSIONS},
        "project_type": get_rubric(ctx.get("project_type"))["project_type"],
        "evaluation_standard": get_rubric(ctx.get("project_type"))["standard"],
        "scoring_weights": get_rubric(ctx.get("project_type"))["weights"],
        "score_band": "Incomplete",
        "confidence": 0,
        "confidence_explanation": "Confidence is 0 because no meaningful project files were detected.",
        "repository_statistics": evidence.get("repository_statistics", {}),
        "repository_completeness_score": 0,
        "evidence_quality": "Incomplete",
        "penalties": [{"factor": reason, "dimension": "overall", "points": 100}],
        "missing_evidence": _missing_evidence_items(evidence),
        "positive_factors": ["Evidence profile generated"],
        "detected_technologies": evidence.get("detected_technologies", []),
        "detected_algorithms": evidence.get("detected_algorithms", []),
        "submitted_project_type": evidence.get("submitted_project_type", ctx.get("project_type", "")),
        "detected_project_type": evidence.get("detected_project_type", ""),
        "detected_project_confidence": evidence.get("detected_project_confidence", 0),
        "architecture_summary": (evidence.get("architecture") or {}).get("summary", ""),
        "evidence_found": (evidence.get("technical_evidence") or {}).get("evidence_found", []),
        "evidence_missing": (evidence.get("technical_evidence") or {}).get("evidence_missing", []),
        "rest_apis_found": evidence.get("rest_apis_found", []),
        "database_usage": evidence.get("database_usage", []),
        "authentication_usage": evidence.get("authentication_usage", []),
        "integrations": evidence.get("integrations", []),
        "top_code_snippets": evidence.get("top_code_snippets", []),
        "community_impact_score": evidence.get("community_impact_score", 0),
        "project_type_justification": (evidence.get("project_type_detection") or {}).get("justification", ""),
        "calibration_explanation": "Evaluation stopped because no meaningful project files were detected.",
        "confidence_sources": _confidence_sources(evidence),
        "blocking_issues": [reason],
        "top_strengths": [],
        "top_weaknesses": [reason],
        "executive_summary": "REJECT - INSUFFICIENT PROJECT CONTENT. Evaluation stopped before scoring because no meaningful project files were detected.",
        "final_reason": reason,
        "recommended_fixes": ["Add source code, documentation, or presentation material before re-running evaluation."],
        "roadmap": ["Add meaningful project files", "Re-submit for YOWON AI evaluation"],
        "deployment_roadmap": ["Add meaningful project files", "Re-submit for YOWON AI evaluation"],
        "contradictions": [],
    }


def calibrate_agent_scores(
    raw_scores: dict[str, int],
    evidence: dict[str, Any],
    project_type: str,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Calibrate each public specialist score using evidence available to that specialist."""
    scores = {key: _calibrate_curve(int(raw_scores.get(key, 0))) for key in DIMENSIONS}
    reasons: dict[str, list[str]] = {key: [] for key in DIMENSIONS}
    checks = evidence.get("checks", {})
    total_penalty = 0
    uncertainty_floor = {
        "technical": 45,
        "security": 45,
        "scalability": 45,
        "innovation": 50,
        "presentation": 45,
        "impact": 45,
    }

    def deduct(dimension: str, points: int, reason: str) -> None:
        nonlocal total_penalty
        remaining = max(0, MAX_TOTAL_PENALTY - total_penalty)
        applied = min(points, remaining)
        if applied <= 0:
            reasons[dimension].append(f"{reason} (penalty cap reached)")
            return
        total_penalty += applied
        scores[dimension] = max(0, scores[dimension] - applied)
        reasons[dimension].append(f"{reason} (-{applied})")

    def uncertainty(dimension: str, reason: str, floor: int | None = None) -> None:
        minimum = uncertainty_floor.get(dimension, 45) if floor is None else floor
        scores[dimension] = max(scores[dimension], minimum)
        reasons[dimension].append(reason)

    def cap(dimension: str, maximum: int, reason: str) -> None:
        if scores[dimension] > maximum:
            scores[dimension] = maximum
            reasons[dimension].append(reason)

    if evidence.get("empty_repository") or (
        not evidence.get("repository_has_content") and evidence.get("data_availability", 0) <= 20
    ):
        for dimension in DIMENSIONS:
            scores[dimension] = 0
            reasons[dimension].append("Repository contains no evaluable content.")
        return scores, reasons

    if checks.get("model_artifact"):
        scores["technical"] = min(100, scores["technical"] + 8)
        scores["innovation"] = max(scores["innovation"], 62)
        reasons["technical"].append("Trained machine learning model artifact detected (+8)")
    if checks.get("dataset_artifact"):
        scores["technical"] = min(100, scores["technical"] + 4)
        scores["impact"] = max(scores["impact"], 50)
        reasons["technical"].append("Dataset artifacts strengthen technical evidence (+4)")
    if checks.get("api_evidence"):
        scores["technical"] = min(100, scores["technical"] + 4)
        scores["scalability"] = min(100, scores["scalability"] + 3)
        reasons["technical"].append("REST/API implementation detected (+4)")
    if checks.get("database_evidence"):
        scores["technical"] = min(100, scores["technical"] + 3)
        reasons["technical"].append("Database integration detected (+3)")
    if checks.get("authentication_evidence"):
        scores["security"] = min(100, scores["security"] + 4)
        reasons["security"].append("Authentication implementation detected (+4)")
    if checks.get("custom_algorithm"):
        scores["innovation"] = min(100, scores["innovation"] + 6)
        reasons["innovation"].append("Custom algorithmic implementation detected (+6)")
    if checks.get("integration_evidence"):
        scores["technical"] = min(100, scores["technical"] + 3)
        scores["impact"] = min(100, scores["impact"] + 2)
        reasons["technical"].append("External integration evidence detected (+3)")
    if checks.get("queue_evidence") or checks.get("vector_database_evidence") or checks.get("agent_system_evidence"):
        scores["scalability"] = min(100, scores["scalability"] + 5)
        scores["innovation"] = min(100, scores["innovation"] + 4)
        reasons["scalability"].append("Advanced architecture component detected (+5)")

    if not checks.get("source_code"):
        cap("technical", 35, "Unable to verify source implementation from repository evidence")
        cap("scalability", 35, "Unable to verify scalability from repository evidence")
    if not checks.get("architecture") or not checks.get("multiple_components"):
        cap("technical", 80, "Technical score above 80 requires architecture evidence and multiple modules")
    if not checks.get("dependency_analysis") or not checks.get("security_practices"):
        if project_type == "Corporate Project":
            cap("security", 35, "Corporate security evidence missing: security score capped at 35")
        else:
            uncertainty("security", "Unable to determine security posture from repository evidence.")
    if not checks.get("no_critical_findings"):
        cap("security", 60, "Critical/high security findings prevent high security score")
    if not checks.get("presentation_material") and not checks.get("documentation"):
        cap("presentation", 35, "Unable to determine presentation quality from repository evidence")
    if project_type != "University Project" and (
        not checks.get("innovation_evidence") or not checks.get("novelty_evidence") or not checks.get("differentiation_evidence")
    ):
        if project_type in ("Hackathon Project", "Startup Pitch", "Research Project"):
            uncertainty("innovation", "Unable to determine innovation level from repository evidence.")
        else:
            cap("innovation", 45, "Innovation evidence unavailable: score capped at 45")
    if project_type not in ("University Project", "Research Project") and (
        not checks.get("impact_evidence") or not checks.get("adoption_evidence") or not checks.get("real_world_value")
    ):
        if project_type in ("Startup Pitch", "Startup Product"):
            cap("impact", 45, "Startup impact evidence unavailable: score capped at 45")
        else:
            uncertainty("impact", "Unable to determine impact level from repository evidence.")
    if not evidence.get("repository_has_content"):
        cap("technical", 20, "No substantive repository evidence")
        cap("security", 30, "No substantive repository evidence")
        cap("scalability", 35, "No substantive repository evidence")
    if not checks.get("tests"):
        if project_type == "Corporate Project":
            cap("technical", 70, "No test evidence: technical score capped at 70")
            deduct("technical", 8, "No test evidence")
        else:
            reasons["technical"].append("Testing evidence missing; confidence reduced rather than treated as failure")
    if not checks.get("security_practices"):
        if project_type == "Corporate Project":
            deduct("security", 12, "No security-practice evidence")
        else:
            reasons["security"].append("Security-practice evidence missing; confidence reduced")
    if not checks.get("documentation"):
        deduct("presentation", 12, "Documentation evidence missing")
    if not checks.get("innovation_evidence"):
        reasons["innovation"].append("Innovation evidence missing; confidence reduced")
    if evidence.get("data_availability", 0) < 40:
        cap("impact", 45, "Insufficient evidence to substantiate impact")

    if project_type == "Research Project":
        research_penalties = (
            ("baseline_comparison", "technical", 10, "No baseline comparison"),
            ("experimental_evidence", "technical", 15, "No experimental evidence"),
            ("experimental_evidence", "impact", 12, "No experimental evidence"),
            ("novelty_evidence", "innovation", 22, "No novelty evidence"),
            ("novelty_evidence", "impact", 10, "No research contribution evidence"),
            ("reproducibility", "technical", 12, "No reproducibility information"),
            ("reproducibility", "presentation", 8, "No reproducibility information"),
            ("citations", "innovation", 8, "No citation or literature-grounding evidence"),
        )
        for check, dimension, points, reason in research_penalties:
            if not checks.get(check):
                deduct(dimension, points, reason)
        # Research is judged on evidence quality, not repository size or polished UI.
        if checks.get("experimental_evidence") and checks.get("reproducibility"):
            scores["technical"] = min(100, scores["technical"] + 5)
        if checks.get("novelty_evidence") and checks.get("baseline_comparison"):
            scores["innovation"] = min(100, scores["innovation"] + 5)

    if project_type in ("Startup Pitch", "Startup Product"):
        if not checks.get("market_evidence"):
            deduct("impact", 28, "No market or customer validation evidence")
        if not checks.get("business_model"):
            deduct("presentation", 15, "No business model evidence")
            deduct("impact", 10, "No business model evidence")
        if not checks.get("competitive_analysis"):
            deduct("innovation", 12, "No competitive analysis evidence")
    if project_type == "Corporate Project":
        if not checks.get("deployment"):
            deduct("technical", 19, "No deployment evidence")
            deduct("scalability", 15, "No deployment evidence")
            deduct("security", 15, "No compliance or deployment-security evidence")
            deduct("impact", 15, "No production-readiness evidence")
        if not checks.get("tests"):
            deduct("technical", 7, "Corporate reliability evidence missing")
    if project_type == "Open Source Project" and not checks.get("contribution_readiness"):
        deduct("presentation", 10, "No contribution-readiness evidence")
        deduct("impact", 8, "No community-readiness evidence")
    if project_type == "Open Source Project":
        stats = evidence.get("repository_statistics", {})
        if evidence.get("complete_project") or (
            stats.get("meaningful_files", 0) >= 40
            and checks.get("source_code")
            and checks.get("documentation")
            and checks.get("architecture")
        ):
            for dimension in ("technical", "scalability", "presentation"):
                scores[dimension] = min(100, scores[dimension] + 5)
            reasons["technical"].append("Open-source rubric: substantial implementation and documentation can score highly")
        if evidence.get("community_impact_score", 0) >= 20:
            scores["impact"] = min(100, scores["impact"] + 5)
            reasons["impact"].append("Open-source rubric: community activity strengthens impact evidence (+5)")
    if project_type in ("Corporate Project", "Enterprise System") and checks.get("deployment") and checks.get("authentication_evidence") and checks.get("database_evidence"):
        scores["technical"] = min(100, scores["technical"] + 4)
        scores["security"] = min(100, scores["security"] + 3)
        scores["scalability"] = min(100, scores["scalability"] + 4)
        reasons["technical"].append("Enterprise architecture evidence detected (+4)")
    if project_type == "University Project" and not checks.get("deployment"):
        for dimension in ("technical", "scalability", "impact"):
            reasons[dimension].append("University rubric: missing deployment is not heavily penalized")
    if project_type == "University Project":
        if checks.get("ml_evidence"):
            scores["innovation"] = max(scores["innovation"], min(70, scores["innovation"] + 12))
            reasons["innovation"].append("University rubric: applied AI/ML implementation counts as innovation")
        if checks.get("real_world_value") or checks.get("source_code"):
            scores["impact"] = max(scores["impact"], min(70, scores["impact"] + 10))
            reasons["impact"].append("University rubric: practical usefulness counts as impact without adoption metrics")
        if checks.get("documentation"):
            scores["presentation"] = max(scores["presentation"], 35)
            reasons["presentation"].append("README/documentation evidence establishes presentation floor")

    if checks.get("documentation"):
        scores["presentation"] = max(scores["presentation"], 20)
    if checks.get("documentation") and evidence.get("repository_statistics", {}).get("documentation_files", 0) > 1:
        scores["presentation"] = max(scores["presentation"], 35)
    if evidence.get("has_report_document") or evidence.get("repository_statistics", {}).get("presentation_files", 0) > 0:
        scores["presentation"] = max(scores["presentation"], 45)

    return scores, reasons


def compute_overall(
    technical: TechnicalReport, security: SecurityReport, innovation: InnovationReport,
    presentation: PresentationReport, risk: RiskReport, *, project_type: str = "Hackathon Project",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rubric = get_rubric(project_type)
    raw_scores = AgentScores(
        technical=technical.technical_score, security=security.security_score,
        scalability=innovation.scalability_score, innovation=innovation.innovation_score,
        presentation=presentation.presentation_score, impact=risk.impact_score,
    ).model_dump()
    raw_scores = {k: max(0, min(100, int(v))) for k, v in raw_scores.items()}
    evidence = evidence or {"checks": {}, "data_availability": 0, "repository_coverage": 0, "json_validity": 0}
    calibrated_scores, calibration_reasons = calibrate_agent_scores(
        raw_scores, evidence, rubric["project_type"]
    )
    scoring_inputs = {
        **calibrated_scores,
        "risk": calibrated_scores["impact"],
        "business_feasibility": calibrated_scores["impact"],
    }
    weighted_score = round(sum(scoring_inputs[k] * weight for k, weight in rubric["weights"].items()))

    penalties = [
        {"factor": reason, "dimension": dimension}
        for dimension, items in calibration_reasons.items() for reason in items
    ]
    material_penalties = [
        item for item in penalties
        if "(-" in item["factor"] or "capped" in item["factor"].lower() or "cap reached" in item["factor"].lower()
    ]
    overall = weighted_score
    if overall > 89 and (evidence.get("data_availability", 0) < 80 or material_penalties):
        penalties.append({"factor": "Exceptional-score evidence gate", "dimension": "overall"})
        overall = 89
    if security.risk_level == "CRITICAL" or calibrated_scores["security"] < 20:
        overall = min(overall, 40)

    overall = round(max(0, overall))
    missing_for_90 = [
        name for name in ("tests", "deployment", "documentation", "architecture", "dependency_analysis", "security_practices")
        if not evidence.get("checks", {}).get(name)
    ]
    if missing_for_90 and overall > 85:
        penalties.append({"factor": f"Exceptional score gate missing: {', '.join(missing_for_90)}", "dimension": "overall"})
        overall = 85
    if evidence.get("trivial_repository") and overall > 25:
        penalties.append({"factor": "1-3 trivial files maximum score cap", "dimension": "overall"})
        overall = 25
    elif evidence.get("tiny_incomplete_project") and overall > 50:
        penalties.append({"factor": "Tiny incomplete project maximum score cap", "dimension": "overall"})
        overall = 50
    elif evidence.get("tiny_repository") and overall > 65 + evidence.get("confidence_bonus", 0):
        penalties.append({"factor": "Tiny project evidence ceiling", "dimension": "overall"})
        overall = min(overall, 65 + evidence.get("confidence_bonus", 0))
    elif evidence.get("small_academic_project") and overall > 70:
        penalties.append({"factor": "Small academic project maximum score cap", "dimension": "overall"})
        overall = 70
    elif evidence.get("small_repository") and overall > 75:
        penalties.append({"factor": "Small project maximum score cap", "dimension": "overall"})
        overall = 75
    if evidence.get("incomplete_project") and overall > 60:
        penalties.append({"factor": "Incomplete project maximum score cap", "dimension": "overall"})
        overall = 60
    if evidence.get("empty_repository"):
        overall = 0
        penalties.append({"factor": "Repository contains no evaluable content.", "dimension": "overall"})
    community_bonus = min(15, int(evidence.get("community_impact_score", 0) * 0.15))
    if community_bonus and overall > 0:
        overall = min(100, overall + community_bonus)
        penalties.append({"factor": f"Community impact signal (+{community_bonus})", "dimension": "overall"})

    overall = round(max(0, overall))
    label = _score_band(overall)
    confidence = _confidence(calibrated_scores, evidence)
    strengths = [f"Strong {k} ({v}/100)" for k, v in calibrated_scores.items() if v >= 80][:5]
    positive_factors = _positive_factors(evidence, strengths)
    weaknesses = [f"Weak {k} ({v}/100)" for k, v in calibrated_scores.items() if v < 60][:5]
    missing = _missing_evidence_items(evidence, penalties)

    return {
        "overall_score": overall, "raw_weighted_score": round(sum(
            ({**raw_scores, "risk": raw_scores["impact"], "business_feasibility": raw_scores["impact"]})[k] * w
            for k, w in rubric["weights"].items()
        )),
        "verdict": _verdict(overall, rubric["project_type"]),
        "risk_level": _infer_risk_level(security, calibrated_scores["security"], overall),
        "agent_scores": calibrated_scores,  # Backward-compatible public alias.
        "raw_agent_scores": raw_scores, "calibrated_agent_scores": calibrated_scores,
        "agent_calibration_reasons": calibration_reasons,
        "project_type": rubric["project_type"], "evaluation_standard": rubric["standard"],
        "submitted_project_type": evidence.get("submitted_project_type", rubric["project_type"]),
        "detected_project_type": evidence.get("detected_project_type", ""),
        "detected_project_confidence": evidence.get("detected_project_confidence", 0),
        "scoring_weights": rubric["weights"], "score_band": label, "confidence": confidence,
        "confidence_explanation": _confidence_explanation(confidence, evidence),
        "confidence_sources": _confidence_sources(evidence),
        "repository_statistics": evidence.get("repository_statistics", {}),
        "repository_completeness_score": evidence.get("repository_completeness_score", 0),
        "evidence_quality": evidence.get("evidence_quality", _score_band(evidence.get("repository_completeness_score", 0))),
        "detected_technologies": evidence.get("detected_technologies", []),
        "detected_algorithms": evidence.get("detected_algorithms", []),
        "architecture_summary": (evidence.get("architecture") or {}).get("summary", ""),
        "evidence_found": (evidence.get("technical_evidence") or {}).get("evidence_found", []),
        "evidence_missing": (evidence.get("technical_evidence") or {}).get("evidence_missing", []),
        "community_impact_score": evidence.get("community_impact_score", 0),
        "project_type_justification": (evidence.get("project_type_detection") or {}).get("justification", ""),
        "calibration_explanation": _calibration_explanation(evidence, penalties),
        "calibration_adjustments": penalties,
        "penalties": penalties, "missing_evidence": missing, "positive_factors": positive_factors,
        "blocking_issues": security.critical_findings[:3] if security.risk_level in ("HIGH", "CRITICAL") else [],
        "top_strengths": (strengths + positive_factors)[:5], "top_weaknesses": (weaknesses + missing)[:5],
    }


def _positive_factors(evidence: dict[str, Any], score_strengths: list[str]) -> list[str]:
    checks = evidence.get("checks", {})
    stats = evidence.get("repository_statistics", {})
    tech_evidence = evidence.get("technical_evidence") or {}
    factors: list[str] = []
    if checks.get("source_code"):
        factors.append("Source code detected")
    if stats.get("documentation_files", 0) > 0 or checks.get("documentation"):
        factors.append("Documentation present")
    if checks.get("tests"):
        factors.append("Automated testing detected")
    if checks.get("ml_evidence"):
        factors.append("Machine learning implementation")
    if checks.get("model_artifact"):
        factors.append("Trained machine learning model detected")
    if checks.get("dataset_artifact") or stats.get("data_files", 0) > 0:
        factors.append("Dataset artifacts detected")
    if checks.get("api_evidence"):
        factors.append("Backend architecture present")
    if checks.get("deployment"):
        factors.append("Deployment files present")
    if checks.get("architecture") or stats.get("source_modules", 0) >= 2:
        factors.append("Modular architecture detected")
    for item in tech_evidence.get("evidence_found", []):
        factors.append(f"{item} detected")
    if evidence.get("detected_technologies"):
        factors.append("Detected technologies: " + ", ".join(evidence["detected_technologies"][:4]))
    if evidence.get("detected_algorithms"):
        factors.append("Detected algorithms: " + ", ".join(evidence["detected_algorithms"][:4]))
    if evidence.get("community_impact_score", 0) > 0:
        factors.append(f"Community impact signal: {evidence['community_impact_score']}/100")
    factors.extend(score_strengths)
    if not factors and stats.get("meaningful_files", 0) > 0 and not evidence.get("empty_repository"):
        factors.append("Meaningful project content detected")
    if not factors:
        factors.append("Evidence profile generated")
    return list(dict.fromkeys(factors))[:8]


def _community_impact_score(gh: dict[str, Any]) -> int:
    stars = int(gh.get("stars") or 0)
    forks = int(gh.get("forks") or 0)
    contributors = int(gh.get("contributors") or 0)
    releases = int(gh.get("releases") or 0)
    score = (
        min(35, stars // 5)
        + min(25, forks // 2)
        + min(25, contributors * 3)
        + min(15, releases * 3)
    )
    return max(0, min(100, score))


def _calibration_explanation(evidence: dict[str, Any], penalties: list[dict[str, Any]]) -> str:
    found = (evidence.get("technical_evidence") or {}).get("evidence_found", [])
    missing = (evidence.get("technical_evidence") or {}).get("evidence_missing", [])
    parts = []
    if found:
        parts.append("Implementation evidence increased confidence: " + ", ".join(found[:6]) + ".")
    if missing:
        parts.append("Missing evidence primarily reduces confidence unless required by project type: " + ", ".join(missing[:6]) + ".")
    if evidence.get("community_impact_score", 0):
        parts.append(f"Community impact contributed a bounded signal ({evidence['community_impact_score']}/100, capped at 15% of final score).")
    if penalties:
        parts.append(f"{len(penalties)} calibration adjustment(s) were applied.")
    return " ".join(parts) or "Scores calibrated from specialist outputs and available project evidence."


def _missing_evidence_items(
    evidence: dict[str, Any],
    penalties: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Return report-ready evidence gaps independently from score penalties."""
    checks = evidence.get("checks", {})
    missing: list[str] = []

    if not checks.get("tests"):
        missing.append("No testing evidence")
    if not checks.get("deployment"):
        missing.append("No deployment evidence")
    if not checks.get("dependency_analysis") and not checks.get("security_practices"):
        missing.append("No security evidence")
    if not checks.get("documentation"):
        missing.append("No documentation evidence")
    if not checks.get("architecture") and not checks.get("multiple_components"):
        missing.append("No scalability evidence")
    if not checks.get("innovation_evidence"):
        missing.append("No innovation evidence")

    for item in penalties or []:
        factor = str(item.get("factor", "")).strip()
        if factor.startswith(("No ", "Insufficient")):
            missing.append(factor)

    if evidence.get("empty_repository"):
        missing.extend([
            "No source-code evidence",
            "Repository contains no evaluable content.",
        ])

    if not missing:
        missing.append("No additional missing evidence detected")
    return list(dict.fromkeys(missing))[:10]


def _confidence_sources(evidence: dict[str, Any]) -> list[str]:
    checks = evidence.get("checks", {})
    stats = evidence.get("repository_statistics", {})
    sources = [
        f"Repository completeness: {evidence.get('repository_completeness_score', 0)}/100",
        "Documentation quality: present" if checks.get("documentation") or stats.get("documentation_files", 0) else "Documentation quality: limited",
        f"Evidence coverage: {evidence.get('repository_coverage', 0)}/100",
        f"Agent agreement: inferred from calibrated specialist scores",
    ]
    if checks.get("model_artifact"):
        sources.append("Trained ML model artifact detected")
    if checks.get("dataset_artifact"):
        sources.append("Dataset artifact detected")
    return sources


def _confidence(agent_map: dict[str, int], evidence: dict[str, Any]) -> int:
    agreement = max(0, 100 - round(pstdev(agent_map.values()) * 2.5))
    checks = evidence.get("checks", {})
    completeness = round(sum(bool(v) for v in checks.values()) / max(1, len(checks)) * 100)
    confidence = round(
        agreement * .15 + completeness * .25 + evidence.get("data_availability", 0) * .20
        + evidence.get("json_validity", 0) * .10 + evidence.get("repository_coverage", 0) * .15
        + evidence.get("repository_completeness_score", 0) * .15
        + evidence.get("confidence_bonus", 0)
    )
    if evidence.get("empty_repository"):
        return 0
    if evidence.get("trivial_repository"):
        return min(confidence, 40)
    if evidence.get("tiny_incomplete_project"):
        return min(confidence, 50)
    if evidence.get("tiny_repository"):
        return min(confidence, 40 + evidence.get("confidence_bonus", 0))
    if evidence.get("small_repository"):
        return min(confidence, 70)
    if evidence.get("repository_completeness_score", 0) >= 80 and evidence.get("data_availability", 0) >= 80:
        return max(confidence, 90)
    return max(0, min(100, confidence))


def _confidence_explanation(confidence: int, evidence: dict[str, Any]) -> str:
    if evidence.get("empty_repository"):
        return "Confidence is below 20 because the repository contains no evaluable content."
    if evidence.get("tiny_repository"):
        return "Confidence is limited to 20-40 because only a tiny amount of content was available."
    if confidence >= 90:
        return "Confidence is high because repository, documentation, security, and context evidence are extensive."
    if confidence >= 70:
        return "Confidence is strong because documentation and repository evidence cover most checks."
    if confidence >= 40:
        return "Confidence is moderate because some evidence exists but important checks are missing."
    return "Confidence is low because evidence coverage is sparse or inconsistent."


def _verdict(score: int, project_type: str) -> str:
    if project_type in ("Corporate Project", "Enterprise System"):
        return "ACCEPT" if score >= 90 else "CONDITIONAL_APPROVE" if score >= 80 else "IMPROVE" if score >= 70 else "REJECT"
    return "ACCEPT" if score >= 85 else "CONDITIONAL_APPROVE" if score >= 70 else "IMPROVE" if score >= 50 else "REJECT"


def _infer_risk_level(security: SecurityReport, calibrated_security: int, overall: int) -> str:
    if security.risk_level == "CRITICAL" or calibrated_security < 20: return "CRITICAL"
    if security.risk_level == "HIGH" or overall < 50: return "HIGH"
    if overall < 75: return "MEDIUM"
    return "LOW"


def detect_contradictions(technical, security, innovation, presentation, risk, brief_missing):
    out = []
    if technical.technical_score > 80 and security.security_score < 50: out.append("High technical score conflicts with low security score")
    if presentation.presentation_score > 80 and brief_missing: out.append("High presentation score despite missing materials")
    if innovation.innovation_score > 85 and innovation.confidence < .5: out.append("High innovation score with low confidence")
    if risk.impact_score > 75 and len(risk.top_risks) >= 4: out.append("Strong impact score despite multiple material risks")
    return out


def format_cross_exam(contradictions: list[str]) -> str:
    return "No major contradictions detected across specialist agents." if not contradictions else "CONTRADICTIONS:\n" + "\n".join(f"- {c}" for c in contradictions)
