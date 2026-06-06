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


def _clean_structure_item(item: str) -> str:
    return str(item).replace("📁", "").replace("📄", "").strip()


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
            "deployment_files": 0, "source_modules": 0, "meaningful_files": 0,
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
        "source_modules": len(modules),
        "meaningful_files": len(set(code_files + docs + presentations + tests + configs + deployments)),
    }


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
    has_repo = bool(gh and not gh.get("error"))
    stats = _repository_statistics(ctx)
    has_documents = bool(
        stats["documentation_files"] or stats["presentation_files"]
        or len(readme) > 80 or (pdf_text and len(pdf_text) > 80) or (ppt_text and len(ppt_text) > 80)
    )
    has_meaningful_text = len(description.strip()) > 80 or has_documents
    repository_has_content = has_repo and bool(
        stats["code_files"] or stats["documentation_files"] or stats["presentation_files"]
        or stats["configuration_files"] or stats["deployment_files"]
        or (readme and readme != "[No README found]" and len(readme.strip()) > 80)
    )
    source_code_exists = stats["code_files"] > 0 or bool(gh.get("python_files"))
    architecture_evidence = source_code_exists and (
        stats["source_modules"] >= 2 or any(term in evidence_text for term in ARCHITECTURE_TERMS)
    )
    multiple_components = stats["source_modules"] >= 2 or stats["code_files"] >= 3
    security_evidence = bool(sec) and (
        bool(sec.get("bandit_issues") is not None)
        or bool(sec.get("dependency_warnings") is not None)
        or bool(sec.get("summary"))
    )
    no_critical_security = not sec.get("secret_findings") and sec.get("risk_level", "LOW") != "CRITICAL"
    novelty = any(x in evidence_text for x in ("novel", "novelty", "differentiator", "unique", "original", "new approach"))
    differentiation = any(x in evidence_text for x in ("competitor", "alternative", "different", "differentiation", "vs ", "compared with"))
    outcomes = any(x in evidence_text for x in IMPACT_TERMS)
    adoption = any(x in evidence_text for x in ("users", "customers", "stars", "downloads", "pilot", "adoption", "traction"))

    checks = {
        "source_code": source_code_exists,
        "architecture": architecture_evidence,
        "multiple_components": multiple_components,
        "documentation": bool(len(readme) > 120 or len(pdf_text) > 120 or len(ppt_text) > 120),
        "presentation_material": bool(ctx.get("ppt") or stats["presentation_files"] or len(readme) > 500 or len(pdf_text) > 500),
        "tests": stats["test_files"] > 0 or any(x in structure for x in ("test", "spec", "__tests__")),
        "deployment": stats["deployment_files"] > 0 or any(x in structure for x in DEPLOYMENT_NAMES),
        "dependency_analysis": security_evidence and (stats["configuration_files"] > 0 or bool(gh.get("dependencies"))),
        "security_practices": security_evidence and any(x in evidence_text for x in SECURITY_TERMS),
        "no_critical_findings": no_critical_security,
        "innovation_evidence": novelty or differentiation or bool(gh.get("topics")),
        "novelty_evidence": novelty,
        "differentiation_evidence": differentiation,
        "impact_evidence": outcomes,
        "adoption_evidence": adoption or int(gh.get("stars") or 0) > 0 or int(gh.get("forks") or 0) > 0,
        "real_world_value": outcomes or any(x in evidence_text for x in ("problem", "workflow", "saves", "reduces", "improves")),
        "baseline_comparison": any(x in evidence_text for x in ("baseline", "benchmark", "compared with", "comparison")),
        "experimental_evidence": any(x in evidence_text for x in ("experiment", "results", "accuracy", "precision", "recall", "f1", "dataset", "evaluation")),
        "reproducibility": any(x in evidence_text for x in ("reproduc", "seed", "methodology", "method", "notebook", "environment")),
        "citations": any(x in evidence_text for x in ("references", "citation", "doi", "arxiv", "et al.", "bibliography")),
        "market_evidence": any(x in evidence_text for x in BUSINESS_TERMS),
        "business_model": any(x in evidence_text for x in ("business model", "pricing", "revenue", "subscription", "gtm", "go-to-market")),
        "competitive_analysis": any(x in evidence_text for x in ("competitor", "competitive", "alternative", "market map")),
        "contribution_readiness": any(x in evidence_text for x in ("contributing", "code of conduct", "issue template", "pull request", "license")),
    }
    total_meaningful = stats["code_files"] + stats["documentation_files"] + stats["presentation_files"] + stats["configuration_files"]
    empty_repository = (has_repo and not total_meaningful and not has_meaningful_text) or (
        not has_repo and not has_meaningful_text
    )
    available = sum((repository_has_content, bool(description.strip()), bool(ctx.get("pdf")), bool(ctx.get("ppt")), security_evidence))
    repository_coverage = min(100, stats["repository_completeness_score"] if "repository_completeness_score" in stats else (
        min(35, stats["code_files"] * 6)
        + min(20, stats["documentation_files"] * 10)
        + min(15, stats["test_files"] * 8)
        + min(15, stats["configuration_files"] * 5)
        + min(15, stats["deployment_files"] * 10)
    ))
    completeness_score = min(
        100,
        min(35, stats["code_files"] * 7)
        + min(15, stats["documentation_files"] * 8)
        + min(15, stats["test_files"] * 8)
        + min(10, stats["configuration_files"] * 4)
        + min(10, stats["deployment_files"] * 10)
        + (10 if checks["architecture"] else 0)
        + (5 if security_evidence else 0),
    )
    sources = parse_sources or {}
    json_validity = round(100 * sum(v == "llm" for v in sources.values()) / len(sources)) if sources else 100
    return {
        "checks": checks,
        "repository_statistics": {**stats, "repository_completeness_score": completeness_score},
        "has_repository": has_repo,
        "repository_has_content": repository_has_content,
        "empty_repository": empty_repository,
        "tiny_repository": 0 < stats["meaningful_files"] <= 3,
        "small_repository": 4 <= stats["meaningful_files"] <= 8,
        "incomplete_project": not checks["source_code"] and not checks["documentation"],
        "data_availability": round(available / 5 * 100),
        "repository_coverage": repository_coverage,
        "repository_completeness_score": completeness_score,
        "json_validity": json_validity,
        "evidence_quality": _score_band(round((completeness_score + repository_coverage + sum(bool(v) for v in checks.values()) / len(checks) * 100) / 3)),
    }


def build_empty_repository_rejection(ctx: dict[str, Any], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = evidence or build_evidence_profile(ctx)
    zero_scores = {key: 0 for key in DIMENSIONS}
    reason = "Repository contains no evaluable content."
    return {
        "overall_score": 0,
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
        "confidence": min(19, _confidence(zero_scores, evidence)),
        "confidence_explanation": "Confidence is very low because the repository has no source, documents, presentations, or meaningful context.",
        "repository_statistics": evidence.get("repository_statistics", {}),
        "repository_completeness_score": 0,
        "evidence_quality": "Incomplete",
        "penalties": [{"factor": reason, "dimension": "overall", "points": 100}],
        "missing_evidence": [reason],
        "positive_factors": [],
        "blocking_issues": [reason],
        "top_strengths": [],
        "top_weaknesses": [reason],
        "executive_summary": "Evaluation rejected before agent execution. Repository contains no evaluable content.",
        "recommended_fixes": ["Add source code, documentation, or presentation material before re-running evaluation."],
        "deployment_roadmap": ["Add evaluable project content", "Re-submit for Sentinel evaluation"],
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

    def deduct(dimension: str, points: int, reason: str) -> None:
        scores[dimension] = max(0, scores[dimension] - points)
        reasons[dimension].append(f"{reason} (-{points})")

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

    if not checks.get("source_code"):
        cap("technical", 20, "No source code evidence: technical score capped at 20")
        cap("scalability", 20, "No source code evidence: scalability score capped at 20")
    if not checks.get("architecture") or not checks.get("multiple_components"):
        cap("technical", 80, "Technical score above 80 requires architecture evidence and multiple modules")
    if not checks.get("dependency_analysis") or not checks.get("security_practices"):
        cap("security", 30, "No security evidence: security score capped at 30")
    if not checks.get("no_critical_findings"):
        cap("security", 60, "Critical/high security findings prevent high security score")
    if not checks.get("presentation_material"):
        cap("presentation", 10, "No presentation or strong documentation evidence: presentation score capped at 10")
    if not checks.get("innovation_evidence") or not checks.get("novelty_evidence") or not checks.get("differentiation_evidence"):
        cap("innovation", 30, "No novelty/differentiation evidence: innovation score capped at 30")
    if not checks.get("impact_evidence") or not checks.get("adoption_evidence") or not checks.get("real_world_value"):
        cap("impact", 30, "No measurable impact/adoption/value evidence: impact score capped at 30")
    if not evidence.get("repository_has_content"):
        cap("technical", 20, "No substantive repository evidence")
        cap("security", 30, "No substantive repository evidence")
        cap("scalability", 35, "No substantive repository evidence")
    if not checks.get("tests"):
        deduct("technical", 8, "No test evidence")
    if not checks.get("security_practices"):
        deduct("security", 12, "No security-practice evidence")
    if not checks.get("documentation"):
        deduct("presentation", 25, "No documentation or presentation evidence")
    if not checks.get("innovation_evidence"):
        deduct("innovation", 18, "No innovation evidence")
    if evidence.get("data_availability", 0) < 40:
        cap("impact", 40, "Insufficient evidence to substantiate impact")

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

    if project_type == "Startup Pitch":
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
    if project_type == "University Project" and not checks.get("deployment"):
        for dimension in ("technical", "scalability", "impact"):
            reasons[dimension].append("University rubric: missing deployment is not heavily penalized")

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
    overall = weighted_score
    if overall > 89 and (evidence.get("data_availability", 0) < 80 or penalties):
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
    if evidence.get("tiny_repository") and overall > 80:
        penalties.append({"factor": "Tiny repository maximum score cap", "dimension": "overall"})
        overall = 80
    if evidence.get("small_repository") and overall > 75:
        penalties.append({"factor": "Small project maximum score cap", "dimension": "overall"})
        overall = 75
    if evidence.get("incomplete_project") and overall > 60:
        penalties.append({"factor": "Incomplete project maximum score cap", "dimension": "overall"})
        overall = 60
    if evidence.get("empty_repository"):
        overall = 0
        penalties.append({"factor": "Repository contains no evaluable content.", "dimension": "overall"})
    if evidence.get("tiny_repository") and evidence.get("repository_completeness_score", 0) < 25 and overall > 25:
        penalties.append({"factor": "1-3 trivial files maximum score cap", "dimension": "overall"})
        overall = 25

    overall = round(max(0, overall))
    label = _score_band(overall)
    confidence = _confidence(calibrated_scores, evidence)
    strengths = [f"Strong {k} ({v}/100)" for k, v in calibrated_scores.items() if v >= 80][:5]
    weaknesses = [f"Weak {k} ({v}/100)" for k, v in calibrated_scores.items() if v < 60][:5]
    missing = list(dict.fromkeys(p["factor"] for p in penalties if p["factor"].startswith(("No ", "Insufficient"))))

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
        "scoring_weights": rubric["weights"], "score_band": label, "confidence": confidence,
        "confidence_explanation": _confidence_explanation(confidence, evidence),
        "repository_statistics": evidence.get("repository_statistics", {}),
        "repository_completeness_score": evidence.get("repository_completeness_score", 0),
        "evidence_quality": evidence.get("evidence_quality", _score_band(evidence.get("repository_completeness_score", 0))),
        "calibration_adjustments": penalties,
        "penalties": penalties, "missing_evidence": missing, "positive_factors": strengths,
        "blocking_issues": security.critical_findings[:3] if security.risk_level in ("HIGH", "CRITICAL") else [],
        "top_strengths": strengths, "top_weaknesses": (weaknesses + missing)[:5],
    }


def _confidence(agent_map: dict[str, int], evidence: dict[str, Any]) -> int:
    agreement = max(0, 100 - round(pstdev(agent_map.values()) * 2.5))
    checks = evidence.get("checks", {})
    completeness = round(sum(bool(v) for v in checks.values()) / max(1, len(checks)) * 100)
    confidence = round(
        agreement * .15 + completeness * .25 + evidence.get("data_availability", 0) * .20
        + evidence.get("json_validity", 0) * .10 + evidence.get("repository_coverage", 0) * .15
        + evidence.get("repository_completeness_score", 0) * .15
    )
    if evidence.get("empty_repository"):
        return min(confidence, 19)
    if evidence.get("tiny_repository"):
        return min(confidence, 40)
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
    if project_type == "Corporate Project":
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
