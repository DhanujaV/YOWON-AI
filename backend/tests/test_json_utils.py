"""Unit tests for JSON parsing utilities."""

import json

from validation.json_utils import extract_json, parse_agent_json
from validation.schemas import ChiefVerdict, TechnicalReport

FALLBACK = {
    "technical_score": 35,
    "strengths": [],
    "weaknesses": ["fallback"],
    "risks": [],
    "confidence": 0.15,
}


def test_extract_json_from_markdown_fence():
    raw = 'Here is output:\n```json\n{"technical_score": 72, "strengths": [], "weaknesses": [], "risks": [], "confidence": 0.8}\n```'
    data = extract_json(raw, label="test")
    assert data is not None
    assert data["technical_score"] == 72


def test_strip_redacted_thinking():
    raw = (
        'reasoning here\n'
        '{"technical_score": 65, "strengths": ["a"], "weaknesses": [], "risks": [], "confidence": 0.7}'
    )
    data = extract_json(raw, label="test")
    assert data is not None
    assert data["technical_score"] == 65


def test_empty_returns_none_not_dict():
    assert extract_json("", label="test") is None
    assert extract_json("no json here", label="test") is None


def test_parse_agent_requires_score():
    raw = '{"strengths": ["ok"], "weaknesses": [], "risks": [], "confidence": 0.5}'
    report, source = parse_agent_json(raw, TechnicalReport, FALLBACK, label="test")
    assert source in ("merged", "fallback")
    assert report.technical_score == 35


def test_parse_agent_llm_success():
    payload = {
        "technical_score": 81,
        "strengths": ["x"],
        "weaknesses": [],
        "risks": [],
        "confidence": 0.9,
    }
    report, source = parse_agent_json(json.dumps(payload), TechnicalReport, FALLBACK, label="test")
    assert source == "llm"
    assert report.technical_score == 81


def test_chief_verdict_string_roadmap_is_not_split_into_characters():
    scores = {
        "technical": 70,
        "security": 70,
        "scalability": 70,
        "innovation": 70,
        "presentation": 70,
        "impact": 70,
    }
    verdict = ChiefVerdict(
        overall_score=70,
        risk_level="MEDIUM",
        verdict="IMPROVE",
        agent_scores=scores,
        raw_agent_scores=scores,
        calibrated_agent_scores=scores,
        deployment_roadmap="Phase 1\n- Improve test coverage\nPhase 2\n- Harden security",
    )
    assert verdict.deployment_roadmap == [
        "Phase 1",
        "Improve test coverage",
        "Phase 2",
        "Harden security",
    ]
