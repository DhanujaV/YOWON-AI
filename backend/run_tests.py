"""Quick validation script (no pytest required)."""
import json
import sys

sys.path.insert(0, ".")

from reports.report_generator import SentinelReport
from validation.json_utils import extract_json, parse_agent_json
from validation.schemas import TechnicalReport

FALLBACK = {
    "technical_score": 35,
    "strengths": [],
    "weaknesses": ["fallback"],
    "risks": [],
    "confidence": 0.15,
}

assert extract_json("") is None
assert extract_json("no json") is None

raw = '```json\n{"technical_score": 72, "strengths": [], "weaknesses": [], "risks": [], "confidence": 0.8}\n```'
assert extract_json(raw, label="t")["technical_score"] == 72

report, source = parse_agent_json(
    json.dumps(
        {
            "technical_score": 81,
            "strengths": ["x"],
            "weaknesses": [],
            "risks": [],
            "confidence": 0.9,
        }
    ),
    TechnicalReport,
    FALLBACK,
    label="t",
)
assert source == "llm" and report.technical_score == 81

fixes_text = SentinelReport._format_fixes(["Fix validation", "Add monitoring"])
assert "Fix validation" in fixes_text

dict_fix = SentinelReport._format_fixes([{"priority": 1, "fix": "Patch auth", "effort": "low"}])
assert "Patch auth" in dict_fix

print("ALL TESTS PASSED")
