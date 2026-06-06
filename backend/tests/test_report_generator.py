"""Tests for PDF report fix normalization."""

from reports.report_generator import SentinelReport


def test_format_fixes_string_list():
    fixes = ["Fix validation", "Add monitoring"]
    text = SentinelReport._format_fixes(fixes)
    assert "Fix validation" in text
    assert "#1:" in text


def test_format_fixes_dict_list():
    fixes = [{"priority": 1, "fix": "Patch auth", "effort": "low"}]
    text = SentinelReport._format_fixes(fixes)
    assert "Patch auth" in text
    assert "Effort: low" in text
