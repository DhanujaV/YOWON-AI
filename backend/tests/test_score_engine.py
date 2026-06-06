"""Calibration and rubric benchmarks for deterministic scoring."""

from scoring.rubrics import PROJECT_TYPES, get_rubric
from scoring.score_engine import build_evidence_profile, compute_overall
from validation.schemas import InnovationReport, PresentationReport, RiskReport, SecurityReport, TechnicalReport


def reports(score: int):
    return (
        TechnicalReport(technical_score=score),
        SecurityReport(security_score=score, risk_level="LOW"),
        InnovationReport(innovation_score=score, scalability_score=score),
        PresentationReport(presentation_score=score),
        RiskReport(impact_score=score),
    )


FULL_EVIDENCE = {
    "checks": {
        "documentation": True, "tests": True, "deployment": True,
        "security_practices": True, "innovation_evidence": True,
        "baseline_comparison": True, "experimental_evidence": True,
        "novelty_evidence": True, "reproducibility": True, "market_evidence": True,
    },
    "repository_has_content": True,
    "data_availability": 100, "repository_coverage": 100, "json_validity": 100,
}


def test_all_rubric_weights_are_normalized():
    for project_type in PROJECT_TYPES:
        assert round(sum(get_rubric(project_type)["weights"].values()), 5) == 1


def test_missing_evidence_calibrates_basic_project_below_excellent():
    result = compute_overall(*reports(90), project_type="Hackathon Project", evidence={
        "checks": {}, "data_availability": 20, "repository_coverage": 10, "json_validity": 100,
    })
    assert result["overall_score"] < 80
    assert result["penalties"]


def test_exceptional_score_requires_exceptional_evidence():
    result = compute_overall(*reports(95), project_type="University Project", evidence=FULL_EVIDENCE)
    assert result["overall_score"] >= 90
    assert result["score_band"] == "Exceptional academic project"


def test_benchmark_score_ordering():
    benchmarks = {
        "Calculator App": 45, "ToDo App": 52, "Voice Classifier": 68,
        "Plant Disease Detection": 72, "Multi-Agent RAG": 82,
        "Startup MVP": 85, "Published Research": 92, "Enterprise Product": 95,
    }
    results = [compute_overall(*reports(score), project_type="Hackathon Project", evidence=FULL_EVIDENCE)["overall_score"] for score in benchmarks.values()]
    assert results == sorted(results)


def test_empty_repository_caps_all_displayed_specialist_scores():
    evidence = build_evidence_profile({
        "description": "",
        "github": {"folder_structure": [], "dependencies": {}, "python_files": [], "readme": "[No README found]"},
        "security": {}, "pdf": {}, "ppt": {},
    })
    result = compute_overall(*reports(85), project_type="Hackathon Project", evidence=evidence)
    calibrated = result["calibrated_agent_scores"]
    assert calibrated["technical"] <= 20
    assert calibrated["security"] <= 20
    assert calibrated["innovation"] <= 10
    assert calibrated["impact"] <= 20
    assert calibrated["presentation"] <= 20
    assert result["overall_score"] <= 20
    assert result["agent_scores"] == calibrated
    assert result["raw_agent_scores"]["technical"] == 85


def test_basic_ml_project_varies_by_project_type():
    evidence = {
        **FULL_EVIDENCE,
        "checks": {
            **FULL_EVIDENCE["checks"],
            "deployment": False,
            "baseline_comparison": False,
            "experimental_evidence": False,
            "novelty_evidence": False,
            "reproducibility": False,
            "market_evidence": False,
        },
    }
    scores = {
        project_type: compute_overall(*reports(78), project_type=project_type, evidence=evidence)["overall_score"]
        for project_type in ("University Project", "Research Project", "Startup Pitch", "Corporate Project")
    }
    assert 70 <= scores["University Project"] <= 80
    assert 55 <= scores["Research Project"] <= 70
    assert 50 <= scores["Startup Pitch"] <= 65
    assert 45 <= scores["Corporate Project"] <= 65
    assert scores["Research Project"] < scores["University Project"]


def test_research_evidence_improves_research_score():
    weak = {
        **FULL_EVIDENCE,
        "checks": {
            **FULL_EVIDENCE["checks"],
            "baseline_comparison": False,
            "experimental_evidence": False,
            "novelty_evidence": False,
            "reproducibility": False,
        },
    }
    weak_result = compute_overall(*reports(80), project_type="Research Project", evidence=weak)
    strong_result = compute_overall(*reports(80), project_type="Research Project", evidence=FULL_EVIDENCE)
    assert strong_result["overall_score"] >= weak_result["overall_score"] + 15
    assert "No novelty evidence" in weak_result["agent_calibration_reasons"]["innovation"]
