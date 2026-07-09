"""Calibration and rubric benchmarks for deterministic scoring."""

from scoring.rubrics import PROJECT_TYPES, get_rubric, is_presentation_enabled
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
    assert result["confidence"] == 0
    assert result["blocking_issues"] == ["Repository contains no evaluable content."]


def test_readme_only_repository_is_insufficient_content():
    ctx = {
        "description": "",
        "github": {
            "folder_structure": ["README.md"],
            "repository_files": ["README.md"],
            "repository_statistics": {
                "total_files": 1,
                "code_files": 0,
                "documentation_files": 1,
                "presentation_files": 0,
                "test_files": 0,
                "configuration_files": 0,
                "deployment_files": 0,
                "data_files": 0,
                "source_modules": 0,
                "meaningful_files": 1,
                "repository_completeness_score": 8,
            },
            "dependencies": {},
            "python_files": [],
            "readme": "# Demo\nOnly a title.",
        },
        "security": {},
        "pdf": {},
        "ppt": {},
    }
    evidence = build_evidence_profile(ctx)
    result = build_empty_repository_rejection(ctx, evidence)
    assert evidence["empty_repository"] is True
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["overall_score"] == 0
    assert result["confidence"] == 0


def test_config_only_repository_is_insufficient_content():
    ctx = {
        "description": "",
        "github": {
            "folder_structure": ["package.json", ".gitignore"],
            "repository_files": ["package.json", ".gitignore"],
            "repository_statistics": {
                "total_files": 2,
                "code_files": 0,
                "documentation_files": 0,
                "presentation_files": 0,
                "test_files": 0,
                "configuration_files": 1,
                "deployment_files": 0,
                "data_files": 0,
                "source_modules": 0,
                "meaningful_files": 1,
                "repository_completeness_score": 4,
            },
            "dependencies": {"package.json": "{}"},
            "python_files": [],
            "readme": "[No README found]",
        },
        "security": {},
        "pdf": {},
        "ppt": {},
    }
    evidence = build_evidence_profile(ctx)
    assert evidence["empty_repository"] is True


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
    assert result["overall_score"] <= 65
    assert result["confidence"] <= 40


def test_tiny_incomplete_project_score_ceiling():
    tiny_incomplete = evidence_with(
        repository_statistics={
            "total_files": 6,
            "code_files": 3,
            "documentation_files": 1,
            "presentation_files": 0,
            "test_files": 0,
            "configuration_files": 1,
            "deployment_files": 0,
            "source_modules": 1,
            "meaningful_files": 6,
            "repository_completeness_score": 42,
        },
        tiny_repository=True,
        tiny_incomplete_project=True,
        repository_completeness_score=42,
        repository_coverage=42,
        checks={
            "architecture": False,
            "multiple_components": False,
            "tests": False,
            "deployment": False,
        },
    )
    result = compute_overall(*reports(95), project_type="Hackathon Project", evidence=tiny_incomplete)
    assert result["overall_score"] <= 50
    assert result["confidence"] <= 50


def test_small_academic_project_score_ceiling():
    small_academic = evidence_with(
        repository_statistics={
            "total_files": 12,
            "code_files": 6,
            "documentation_files": 2,
            "presentation_files": 0,
            "test_files": 1,
            "configuration_files": 1,
            "deployment_files": 0,
            "source_modules": 2,
            "meaningful_files": 10,
            "repository_completeness_score": 64,
        },
        tiny_repository=False,
        tiny_incomplete_project=False,
        small_repository=True,
        small_academic_project=True,
        repository_completeness_score=64,
        repository_coverage=64,
    )
    result = compute_overall(*reports(98), project_type="University Project", evidence=small_academic)
    assert result["overall_score"] <= 70


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
    assert missing_tests["confidence"] < full["confidence"]
    assert any("confidence reduced" in r.lower() for r in missing_tests["agent_calibration_reasons"]["technical"])


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
    assert empty_result["confidence"] == 0
    assert 20 <= tiny_result["confidence"] <= 40
    assert full_result["confidence"] >= 90


def test_positive_factors_generated_from_repository_evidence():
    evidence = evidence_with(
        checks={**FULL_CHECKS, "ml_evidence": True, "api_evidence": True},
        repository_statistics={**FULL_EVIDENCE["repository_statistics"], "data_files": 1},
    )
    result = compute_overall(*reports(75), project_type="University Project", evidence=evidence)
    assert "Documentation present" in result["positive_factors"]
    assert "Automated testing detected" in result["positive_factors"]
    assert "Machine learning implementation" in result["positive_factors"]
    assert "Backend architecture present" in result["positive_factors"]


def test_missing_evidence_generated_separately_from_penalties():
    evidence = {
        "checks": {
            "tests": False,
            "deployment": False,
            "dependency_analysis": False,
            "security_practices": False,
            "documentation": False,
            "architecture": False,
            "multiple_components": False,
            "innovation_evidence": False,
        },
        "repository_statistics": {},
        "data_availability": 30,
        "repository_coverage": 20,
        "repository_completeness_score": 20,
        "json_validity": 100,
    }
    result = compute_overall(
        TechnicalReport(technical_score=60),
        SecurityReport(security_score=60),
        InnovationReport(innovation_score=60, scalability_score=60),
        PresentationReport(presentation_score=60),
        RiskReport(impact_score=60),
        project_type="Hackathon Project",
        evidence=evidence,
    )
    assert "No testing evidence" in result["missing_evidence"]
    assert "No deployment evidence" in result["missing_evidence"]
    assert "No security evidence" in result["missing_evidence"]
    assert "No documentation evidence" in result["missing_evidence"]
    assert "No scalability evidence" in result["missing_evidence"]
    assert "No innovation evidence" in result["missing_evidence"]
    assert result["missing_evidence"] != result["penalties"]


def test_code_evidence_improves_small_technical_project_explanation():
    evidence = evidence_with(
        checks={
            **FULL_CHECKS,
            "tests": False,
            "deployment": False,
            "api_evidence": True,
            "database_evidence": True,
            "authentication_evidence": True,
            "custom_algorithm": True,
        },
        repository_statistics={
            **FULL_EVIDENCE["repository_statistics"],
            "total_files": 6,
            "code_files": 3,
            "test_files": 0,
            "deployment_files": 0,
            "meaningful_files": 5,
        },
        tiny_repository=True,
        technical_evidence={
            "evidence_found": ["REST API", "Database", "Authentication", "Custom algorithm"],
            "evidence_missing": ["Testing", "Docker/deployment"],
        },
        detected_technologies=["FastAPI", "SQLAlchemy"],
        detected_algorithms=["Random Forest"],
        community_impact_score=20,
    )
    result = compute_overall(*reports(70), project_type="Hackathon Project", evidence=evidence)
    assert "REST API detected" in result["positive_factors"]
    assert "FastAPI" in result["detected_technologies"]
    assert "Random Forest" in result["detected_algorithms"]
    assert "Implementation evidence increased confidence" in result["calibration_explanation"]


def test_university_ai_project_not_penalized_like_startup():
    university_ai = evidence_with(
        checks={
            "market_evidence": False,
            "business_model": False,
            "competitive_analysis": False,
            "adoption_evidence": False,
            "deployment": False,
            "ml_evidence": True,
            "api_evidence": True,
        },
        repository_completeness_score=76,
        repository_coverage=76,
    )
    result = compute_overall(*reports(82), project_type="University Project", evidence=university_ai)
    assert result["overall_score"] >= 60
    assert result["agent_scores"]["innovation"] >= 60
    assert result["agent_scores"]["impact"] >= 55


def test_presentation_disabled_for_non_hackathon_projects():
    with_readme_docs = evidence_with(
        checks={"presentation_material": False, "documentation": True},
        repository_statistics={**FULL_EVIDENCE["repository_statistics"], "documentation_files": 2, "presentation_files": 0},
        submitted_project_type="University Project",
        detected_project_type="Hackathon Project",
    )
    result = compute_overall(*reports(20), project_type="University Project", evidence=with_readme_docs)
    assert is_presentation_enabled("Hackathon Project") is True
    assert is_presentation_enabled("University Project") is False
    assert "presentation" not in result["agent_scores"]
    assert "presentation" not in result["raw_agent_scores"]
    assert "presentation" not in result["calibrated_agent_scores"]
    assert "presentation" not in result["scoring_weights"]
    assert all(item.get("dimension") != "presentation" for item in result["penalties"])


def test_hackathon_uses_submitted_type_even_when_detection_disagrees():
    evidence = evidence_with(
        submitted_project_type="Hackathon Project",
        detected_project_type="Research Project",
    )
    result = compute_overall(*reports(65), project_type="Hackathon Project", evidence=evidence)
    assert result["agent_scores"]["presentation"] >= 0
    assert result["scoring_weights"]["presentation"] == .10


def test_ml_model_and_dataset_artifacts_raise_evidence_quality():
    ctx = {
        "description": "Image classifier with training pipeline and evaluation metrics.",
        "project_type": "University Project",
        "github": {
            "folder_structure": [
                "src/train.py",
                "models/classifier.onnx",
                "data/features.csv",
                "README.md",
            ],
            "repository_files": [
                "src/train.py",
                "models/classifier.onnx",
                "data/features.csv",
                "README.md",
            ],
            "dependencies": {"requirements.txt": "torch\nsklearn"},
            "python_files": ["src/train.py"],
            "readme": "A documented machine learning project with dataset and model outputs.",
        },
        "security": {"summary": "No critical findings", "risk_level": "LOW", "dependency_warnings": []},
        "pdf": {},
        "ppt": {},
    }
    evidence = build_evidence_profile(ctx)
    result = compute_overall(*reports(65), project_type="University Project", evidence=evidence)
    assert evidence["checks"]["model_artifact"] is True
    assert evidence["checks"]["dataset_artifact"] is True
    assert result["agent_scores"]["technical"] >= 55
    assert "Trained machine learning model detected" in result["positive_factors"]
    assert "Dataset artifacts detected" in result["positive_factors"]
    assert any("Repository completeness" in source for source in result["confidence_sources"])


def test_missing_innovation_is_uncertainty_not_negative_evidence():
    missing_innovation = evidence_with(checks={
        "innovation_evidence": False,
        "novelty_evidence": False,
        "differentiation_evidence": False,
    })
    result = compute_overall(*reports(55), project_type="Hackathon Project", evidence=missing_innovation)
    assert result["agent_scores"]["innovation"] >= 50
    assert any("Unable to determine innovation" in item for item in result["agent_calibration_reasons"]["innovation"])


def test_penalty_cap_limits_stacked_deductions():
    weak_corporate = evidence_with(checks={
        "tests": False,
        "deployment": False,
        "security_practices": False,
        "dependency_analysis": False,
    })
    result = compute_overall(*reports(80), project_type="Corporate Project", evidence=weak_corporate)
    applied = []
    for items in result["agent_calibration_reasons"].values():
        for item in items:
            if "(-" in item:
                applied.append(int(item.rsplit("(-", 1)[1].split(")", 1)[0]))
    assert sum(applied) <= 45


def test_score_engine_key_error_prevention():
    # Pass None for presentation report and test a project type that includes/excludes presentation
    t, s, i, _, r = reports(75)
    evidence = {"checks": {}, "data_availability": 80}
    
    import pytest
    from validation.schemas import EvaluationIncompleteException

    # Try Hackathon Project (presentation enabled) with presentation=None -> must raise exception
    with pytest.raises(EvaluationIncompleteException):
        compute_overall(
            t, s, i, None, r,
            project_type="Hackathon Project",
            evidence=evidence
        )

    # Try University Project (presentation disabled) with presentation=None -> should succeed since presentation is disabled
    result_university = compute_overall(
        t, s, i, None, r,
        project_type="University Project",
        evidence=evidence
    )
    assert result_university["overall_score"] > 0
    assert "presentation" not in result_university["agent_scores"]
