"""Calibration and rubric benchmarks for deterministic scoring."""

from scoring.rubrics import PROJECT_TYPES, get_rubric
from scoring.score_engine import (
    build_empty_repository_rejection,
    build_evidence_profile,
    compute_overall,
)
from validation.schemas import (
    InnovationReport,
    PresentationReport,
    RiskReport,
    SecurityReport,
    TechnicalReport,
)


def reports(score: int, *, risk_level: str = "LOW"):
    return (
        TechnicalReport(technical_score=score),
        SecurityReport(security_score=score, risk_level=risk_level),
        InnovationReport(innovation_score=score, scalability_score=score),
        PresentationReport(presentation_score=score),
        RiskReport(impact_score=score),
    )


FULL_CHECKS = {
    "source_code": True,
    "architecture": True,
    "multiple_components": True,
    "documentation": True,
    "presentation_material": True,
    "tests": True,
    "deployment": True,
    "dependency_analysis": True,
    "security_practices": True,
    "no_critical_findings": True,
    "innovation_evidence": True,
    "novelty_evidence": True,
    "differentiation_evidence": True,
    "impact_evidence": True,
    "adoption_evidence": True,
    "real_world_value": True,
    "baseline_comparison": True,
    "experimental_evidence": True,
    "reproducibility": True,
    "citations": True,
    "market_evidence": True,
    "business_model": True,
    "competitive_analysis": True,
    "contribution_readiness": True,
}

FULL_EVIDENCE = {
    "checks": FULL_CHECKS,
    "repository_statistics": {
        "total_files": 60,
        "code_files": 30,
        "documentation_files": 6,
        "presentation_files": 1,
        "test_files": 10,
        "configuration_files": 6,
        "deployment_files": 3,
        "source_modules": 8,
        "meaningful_files": 56,
        "repository_completeness_score": 100,
    },
    "repository_has_content": True,
    "empty_repository": False,
    "tiny_repository": False,
    "small_repository": False,
    "incomplete_project": False,
    "data_availability": 100,
    "repository_coverage": 100,
    "repository_completeness_score": 100,
    "json_validity": 100,
    "evidence_quality": "Exceptional",
}


def evidence_with(**overrides):
    evidence = {
        **FULL_EVIDENCE,
        "checks": {**FULL_CHECKS},
        "repository_statistics": {**FULL_EVIDENCE["repository_statistics"]},
    }
    checks = overrides.pop("checks", {})
    evidence["checks"].update(checks)
    evidence.update(overrides)
    return evidence


def test_all_rubric_weights_are_normalized():
    for project_type in PROJECT_TYPES:
        assert round(sum(get_rubric(project_type)["weights"].values()), 5) == 1


def test_empty_repository_rejection_payload():
    ctx = {
        "description": "",
        "github": {"folder_structure": [], "dependencies": {}, "python_files": [], "readme": "[No README found]"},
        "security": {},
        "pdf": {},
        "ppt": {},
    }
    evidence = build_evidence_profile(ctx)
    result = build_empty_repository_rejection(ctx, evidence)
    assert evidence["empty_repository"] is True
    assert result["overall_score"] == 0
    assert result["verdict"] == "REJECT"
    assert result["risk_level"] == "CRITICAL"
    assert result["confidence"] < 20
    assert result["blocking_issues"] == ["Repository contains no evaluable content."]


def test_empty_repository_caps_all_displayed_specialist_scores():
    evidence = build_evidence_profile({
        "description": "",
        "github": {"folder_structure": [], "dependencies": {}, "python_files": [], "readme": "[No README found]"},
        "security": {},
        "pdf": {},
        "ppt": {},
    })
    result = compute_overall(*reports(85), project_type="Hackathon Project", evidence=evidence)
    assert result["overall_score"] == 0
    assert all(score == 0 for score in result["calibrated_agent_scores"].values())
    assert result["score_band"] == "Incomplete"


def test_tiny_repository_stays_low_score():
    tiny = evidence_with(
        repository_statistics={
            "total_files": 2,
            "code_files": 1,
            "documentation_files": 1,
            "presentation_files": 0,
            "test_files": 0,
            "configuration_files": 0,
            "deployment_files": 0,
            "source_modules": 1,
            "meaningful_files": 2,
            "repository_completeness_score": 18,
        },
        tiny_repository=True,
        repository_completeness_score=18,
        repository_coverage=18,
        checks={
            "architecture": False,
            "multiple_components": False,
            "tests": False,
            "deployment": False,
            "dependency_analysis": False,
            "security_practices": False,
            "presentation_material": False,
        },
    )
    result = compute_overall(*reports(95), project_type="Hackathon Project", evidence=tiny)
    assert result["overall_score"] <= 25
    assert result["confidence"] <= 40


def test_startup_pitch_without_business_evidence_is_penalized():
    no_business = evidence_with(checks={
        "market_evidence": False,
        "business_model": False,
        "competitive_analysis": False,
    })
    result = compute_overall(*reports(90), project_type="Startup Pitch", evidence=no_business)
    assert result["overall_score"] < 70
    assert any("market" in r.lower() for r in result["agent_calibration_reasons"]["impact"])


def test_corporate_project_without_deployment_is_reduced():
    no_deployment = evidence_with(checks={"deployment": False})
    result = compute_overall(*reports(90), project_type="Corporate Project", evidence=no_deployment)
    assert result["overall_score"] <= 75
    assert any("deployment" in r.lower() for r in result["agent_calibration_reasons"]["technical"])


def test_research_project_without_experiments_is_reduced():
    weak_research = evidence_with(checks={
        "baseline_comparison": False,
        "experimental_evidence": False,
        "novelty_evidence": False,
        "reproducibility": False,
        "citations": False,
    })
    result = compute_overall(*reports(90), project_type="Research Project", evidence=weak_research)
    assert result["overall_score"] < 65
    assert any("experimental" in r.lower() for r in result["agent_calibration_reasons"]["technical"])


def test_university_project_not_heavily_penalized_for_missing_deployment():
    no_deployment = evidence_with(checks={"deployment": False})
    university = compute_overall(*reports(85), project_type="University Project", evidence=no_deployment)
    corporate = compute_overall(*reports(85), project_type="Corporate Project", evidence=no_deployment)
    assert university["overall_score"] > corporate["overall_score"]
    assert any("not heavily penalized" in r for r in university["agent_calibration_reasons"]["technical"])


def test_exceptional_score_requires_all_core_evidence():
    full = compute_overall(*reports(100), project_type="University Project", evidence=FULL_EVIDENCE)
    missing_tests = compute_overall(
        *reports(100),
        project_type="University Project",
        evidence=evidence_with(checks={"tests": False}),
    )
    assert full["overall_score"] >= 90
    assert full["score_band"] == "Exceptional"
    assert missing_tests["overall_score"] <= 85


def test_confidence_tracks_evidence_completeness():
    empty = build_evidence_profile({
        "description": "",
        "github": {"folder_structure": [], "dependencies": {}, "python_files": [], "readme": "[No README found]"},
        "security": {},
        "pdf": {},
        "ppt": {},
    })
    tiny = evidence_with(tiny_repository=True, repository_completeness_score=20, repository_coverage=20)
    empty_result = compute_overall(*reports(70), project_type="Hackathon Project", evidence=empty)
    tiny_result = compute_overall(*reports(70), project_type="Hackathon Project", evidence=tiny)
    full_result = compute_overall(*reports(100), project_type="Hackathon Project", evidence=FULL_EVIDENCE)
    assert empty_result["confidence"] < 20
    assert 20 <= tiny_result["confidence"] <= 40
    assert full_result["confidence"] >= 90
