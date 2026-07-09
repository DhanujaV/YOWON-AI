"""
test_enterprise_suite.py — Determinism Stress Tests & Regression Benchmarks.

Verifies:
1. Determinism stress test (50 repeated trials on the same inputs yields identical scores).
2. Regression suite using a fixed benchmark set of repository profiles with expected score ranges.
"""
from __future__ import annotations

import statistics
import pytest
from scoring.score_engine import compute_overall
from validation.schemas import (
    TechnicalReport,
    SecurityReport,
    InnovationReport,
    PresentationReport,
    RiskReport,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper to construct mock specialist agent reports
# ─────────────────────────────────────────────────────────────────────────────

def _make_reports(
    tech_score: int,
    sec_score: int,
    innov_score: int,
    pres_score: int,
    risk_score: int,
    risk_level: str = "LOW"
) -> tuple:
    return (
        TechnicalReport(technical_score=tech_score, strengths=["Clean code"], weaknesses=[]),
        SecurityReport(security_score=sec_score, risk_level=risk_level, critical_findings=[]),
        InnovationReport(innovation_score=innov_score, scalability_score=innov_score, differentiators=["Unique ML model"]),
        PresentationReport(presentation_score=pres_score, strengths=["Clear slides"]),
        RiskReport(impact_score=risk_score, top_risks=["Scale bottlenecks"])
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Determinism Stress Test
# ─────────────────────────────────────────────────────────────────────────────

def test_determinism_stress_scoring():
    """
    Stress test: Runs 50 repeated evaluations on identical inputs.
    Asserts that the computed metrics and overall score are strictly deterministic (zero variance).
    """
    scores = []
    verdicts = []
    calibrated_tech = []
    
    # Define a static inputs profiles
    tech, security, innovation, presentation, risk = _make_reports(
        tech_score=85,
        sec_score=75,
        innov_score=80,
        pres_score=90,
        risk_score=70,
        risk_level="MEDIUM"
    )
    
    evidence = {
        "repository_has_content": True,
        "data_availability": 100,
        "checks": {
            "source_code": True,
            "architecture": True,
            "documentation": True,
            "tests": True,
            "dependency_analysis": True,
            "security_practices": True,
            "no_critical_findings": True
        },
        "repository_statistics": {
            "total_files": 45,
            "code_files": 25,
            "documentation_files": 4,
            "test_files": 6,
            "total_loc": 2500,
            "average_loc": 100,
            "languages": ["python", "javascript"]
        }
    }


    # Run 50 times
    for _ in range(50):
        result = compute_overall(
            tech,
            security,
            innovation,
            presentation,
            risk,
            project_type="Hackathon Project",
            evidence=evidence
        )
        scores.append(result["overall_score"])
        verdicts.append(result["verdict"])
        calibrated_tech.append(result["calibrated_agent_scores"]["technical"])

    # Assert zero variance
    assert len(set(scores)) == 1, f"Overall scores were not identical: {set(scores)}"
    assert len(set(verdicts)) == 1, f"Verdicts were not identical: {set(verdicts)}"
    assert len(set(calibrated_tech)) == 1, f"Calibrated scores were not identical: {set(calibrated_tech)}"
    
    # Calculate statistics to prove determinism
    variance = statistics.variance(scores) if len(scores) > 1 else 0.0
    assert variance == 0.0, f"Score variance must be exactly 0, got {variance}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Regression Benchmark Suite
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "profile_name, tech_val, sec_val, innov_val, pres_val, risk_val, sec_level, expected_range",
    [
        # Profile A: High-Quality Production-Ready Project (Excellent scores, low risk)
        ("high_quality_production", 95, 90, 88, 92, 85, "LOW", (70, 85)),
        
        # Profile B: Average Prototype Project (Decent logic, average tech, no tests)
        ("average_prototype", 72, 70, 75, 68, 65, "MEDIUM", (55, 70)),

        
        # Profile C: Vulnerable / High Risk Project (Has critical vulnerabilities / high security risk)
        ("vulnerable_project", 80, 45, 70, 75, 60, "HIGH", (50, 70)),
        
        # Profile D: Empty / Minimal Project (Fails checks, low scores)
        ("empty_minimal", 40, 50, 30, 20, 35, "MEDIUM", (20, 50)),
    ]
)
def test_regression_benchmark_ranges(
    profile_name, tech_val, sec_val, innov_val, pres_val, risk_val, sec_level, expected_range
):
    """
    Regression Suite: Ensures that fixed benchmark repository profiles map to expected score ranges.
    Guarantees no score drifts or regressions across version upgrades.
    """
    tech, security, innovation, presentation, risk = _make_reports(
        tech_score=tech_val,
        sec_score=sec_val,
        innov_score=innov_val,
        pres_score=pres_val,
        risk_score=risk_val,
        risk_level=sec_level
    )
    
    # Setup standard evidence based on quality profile
    has_evidence = (profile_name != "empty_minimal")
    evidence = {
        "repository_has_content": True,
        "data_availability": 100,
        "checks": {
            "source_code": has_evidence,
            "architecture": has_evidence,
            "documentation": has_evidence,
            "tests": (profile_name == "high_quality_production"),
            "dependency_analysis": has_evidence,
            "security_practices": (profile_name == "high_quality_production"),
            "no_critical_findings": (sec_level == "LOW")
        },
        "repository_statistics": {
            "total_files": 100 if profile_name == "high_quality_production" else 10,
            "code_files": 60 if profile_name == "high_quality_production" else 5,
            "total_loc": 5000 if profile_name == "high_quality_production" else 200,
        }
    }

    
    result = compute_overall(
        tech,
        security,
        innovation,
        presentation,
        risk,
        project_type="Hackathon Project",
        evidence=evidence
    )
    
    overall_score = result["overall_score"]
    min_expected, max_expected = expected_range
    
    assert min_expected <= overall_score <= max_expected, (
        f"Regression failure for profile '{profile_name}': "
        f"Overall score {overall_score} fell outside expected range [{min_expected}, {max_expected}]."
    )
