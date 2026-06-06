"""Calibration and rubric benchmarks for deterministic scoring."""

from scoring.rubrics import PROJECT_TYPES, get_rubric
from scoring.score_engine import compute_overall
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
    "checks": {"documentation": True, "tests": True, "deployment": True, "security_practices": True, "innovation_evidence": True},
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
