"""PDF report generation for YOWON AI."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

try:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, String
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except Exception:  # pragma: no cover - importable in minimal CI environments
    REPORTLAB_AVAILABLE = False
    colors = type("C", (), {"HexColor": lambda value: value, "white": "#ffffff"})
    TA_CENTER = TA_LEFT = 0
    A4 = (595.27, 841.89)

    def ParagraphStyle(*args, **kwargs):
        return {}

    def getSampleStyleSheet():
        normal = ParagraphStyle("Normal")
        return {
            "Normal": normal,
            "Heading1": ParagraphStyle("Heading1", parent=normal),
            "Heading2": ParagraphStyle("Heading2", parent=normal),
        }

    cm = 1

    class HRFlowable:
        def __init__(self, *args, **kwargs):
            pass

    class PageBreak:
        pass

    def Paragraph(text, style=None):
        return str(text)

    class SimpleDocTemplate:
        def __init__(self, filename, *args, **kwargs):
            self.filename = filename

        def build(self, story):
            raise RuntimeError("ReportLab is required to generate PDF files")

    def Spacer(width, height):
        return ""

    class Table:
        def __init__(self, *args, **kwargs):
            pass

        def setStyle(self, *args, **kwargs):
            pass

    class TableStyle(list):
        pass

    class Drawing:
        def __init__(self, *args, **kwargs):
            pass

        def add(self, item):
            pass

    class VerticalBarChart:
        pass

    def Circle(*args, **kwargs):
        return ""

    def Line(*args, **kwargs):
        return ""

    def Polygon(*args, **kwargs):
        return ""

    def String(*args, **kwargs):
        return ""

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional runtime validation
    PdfReader = None

try:
    from backend.config import REPORT_DIR
except Exception:  # pragma: no cover
    REPORT_DIR = Path(__file__).parent

REPORT_DIR.mkdir(parents=True, exist_ok=True)

C_DARK = colors.HexColor("#050816")
C_PRIMARY = colors.HexColor("#00AFC4")
C_GREEN = colors.HexColor("#00B878")
C_YELLOW = colors.HexColor("#F59E0B")
C_RED = colors.HexColor("#EF4444")
C_LIGHT = colors.HexColor("#EAFBFF")
C_GRAY = colors.HexColor("#475569")
C_BORDER = colors.HexColor("#B9E7EF")
C_ACCENT = colors.HexColor("#7C3AED")

INTERNAL_REPORT_KEYS = {
    "raw_scores",
    "calibrated_scores",
    "calibration_reasons",
    "raw_agent_scores",
    "calibrated_agent_scores",
    "agent_calibration_reasons",
    "calibration_adjustments",
    "raw_weighted_score",
}

DEFAULT_ROADMAP = [
    "Stabilize evidence package with README, architecture notes, and setup instructions",
    "Add automated tests and publish repeatable validation results",
    "Harden security, dependency, and secrets-management controls",
    "Prepare deployment assets, observability, and rollback steps",
    "Re-run YOWON AI evaluation before production or demo release",
]

DEFAULT_MISSING_EVIDENCE = [
    "No testing evidence",
    "No deployment evidence",
    "No security evidence",
    "No documentation evidence",
    "No scalability evidence",
    "No innovation evidence",
]

DEFAULT_POSITIVE_FACTORS = ["Evidence profile generated"]


def _presentation_enabled_from_verdict(verdict_data: dict[str, Any]) -> bool:
    return str(verdict_data.get("submitted_project_type") or verdict_data.get("project_type") or "").strip() == "Hackathon Project"


try:
    from logging_config import get_logger
except Exception:  # pragma: no cover
    from backend.logging_config import get_logger


logger = get_logger(__name__)


class PDFGenerationError(RuntimeError):
    """Raised when a report cannot be produced as a valid PDF."""


def validate_pdf_file(path: str | Path) -> int:
    """Validate a generated file is a real PDF and return its byte size."""
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise PDFGenerationError(f"PDF file was not created: {pdf_path}")
    size = pdf_path.stat().st_size
    if size <= 0:
        raise PDFGenerationError(f"PDF file is empty: {pdf_path}")
    with pdf_path.open("rb") as handle:
        header = handle.read(5)
    if header != b"%PDF-":
        raise PDFGenerationError(f"Generated file is not a PDF: {pdf_path}")
    if PdfReader is not None:
        try:
            reader = PdfReader(str(pdf_path))
            if len(reader.pages) <= 0:
                raise PDFGenerationError(f"Generated PDF has no readable pages: {pdf_path}")
        except PDFGenerationError:
            raise
        except Exception as exc:
            raise PDFGenerationError(f"Generated PDF failed readability validation: {exc}") from exc
    return size


def _hex(color: Any) -> str:
    return getattr(color, "hexval", lambda: str(color))()


def _verdict_color(verdict: str) -> Any:
    return {"ACCEPT": C_GREEN, "CONDITIONAL_APPROVE": C_PRIMARY, "IMPROVE": C_YELLOW, "REJECT": C_RED}.get(verdict, C_GRAY)


def _risk_color(risk: str) -> Any:
    return {"LOW": C_GREEN, "MEDIUM": C_YELLOW, "HIGH": colors.HexColor("#F97316"), "CRITICAL": C_RED}.get(risk, C_GRAY)


def _score_color(score: float) -> Any:
    if score >= 80:
        return C_GREEN
    if score >= 50:
        return C_YELLOW
    return C_RED


def _safe_score(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except Exception:
        return 0.0


def _normalize_list(value: Any, fallback: list[str] | None = None, *, limit: int = 12) -> list[str]:
    if value is None or value == "":
        return list(fallback or [])

    if isinstance(value, dict):
        value = [value]

    if isinstance(value, list):
        raw_items: list[str] = []
        if len(value) > 3 and all(isinstance(item, str) and len(item) <= 1 for item in value):
            return _normalize_list("".join(value), fallback=fallback, limit=limit)
        for item in value:
            if isinstance(item, dict):
                text = item.get("fix") or item.get("step") or item.get("action") or item.get("factor") or item
            else:
                text = item
            raw_items.extend(_normalize_list(str(text), fallback=[], limit=limit))
        unique = [item for item in dict.fromkeys(raw_items) if item and len(item) > 1]
        return unique[:limit] or list(fallback or [])

    text = str(value).strip()
    if not text:
        return list(fallback or [])
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return _normalize_list(parsed, fallback=fallback, limit=limit)
        except Exception:
            pass

    text = re.sub(r"(?i)\s+(?=phase\s+\d+[:.\-])", "\n", text)
    text = re.sub(r"\s+(?=\d+[.)]\s+[A-Z])", "\n", text)
    parts = re.split(r"\r?\n|(?:\s*[;]\s*)", text)
    items = []
    for part in parts:
        cleaned = re.sub(r"^\s*(?:[-*+]|->|=>|[0-9]+[.)]|[A-Za-z][.)])\s*", "", part).strip()
        cleaned = cleaned.strip(" -\t")
        if cleaned and len(cleaned) > 1:
            items.append(cleaned)
    return list(dict.fromkeys(items))[:limit] or list(fallback or [])


class YowonReport:
    """Builder for a professional YOWON AI PDF report."""

    def __init__(self, project_name: str, report_id: str):
        if not REPORTLAB_AVAILABLE:
            raise PDFGenerationError("ReportLab is not available; cannot generate PDF")
        self.project_name = project_name or "Untitled Project"
        self.report_id = report_id
        self.filename = REPORT_DIR / f"yowon_report_{report_id}.pdf"
        self.story: list[Any] = []
        self.styles = getSampleStyleSheet()
        self._define_styles()

    def _base_style(self, name: str) -> Any:
        return self.styles.get(name) or self.styles.get("Normal") or ParagraphStyle("Normal")

    def _define_styles(self) -> None:
        normal = self._base_style("Normal")
        self.h1 = ParagraphStyle("YowonH1", parent=self._base_style("Heading1"), fontSize=22, leading=27, textColor=C_DARK, spaceAfter=8, fontName="Helvetica-Bold")
        self.h2 = ParagraphStyle("YowonH2", parent=self._base_style("Heading2"), fontSize=14, leading=18, textColor=C_PRIMARY, spaceBefore=4, spaceAfter=5, fontName="Helvetica-Bold", keepWithNext=True)
        self.body = ParagraphStyle("YowonBody", parent=normal, fontSize=9, leading=13, textColor=C_DARK, alignment=TA_LEFT, splitLongWords=True, wordWrap="CJK")
        self.bullet = ParagraphStyle("YowonBullet", parent=self.body, leftIndent=14, firstLineIndent=-8, spaceAfter=3)
        self.table_cell = ParagraphStyle("YowonTableCell", parent=normal, fontSize=8, leading=11, textColor=C_DARK, splitLongWords=True, wordWrap="CJK")
        self.cover_title = ParagraphStyle("YowonCoverTitle", parent=normal, alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=32, leading=38, textColor=C_DARK)
        self.center = ParagraphStyle("YowonCenter", parent=normal, alignment=TA_CENTER, fontSize=10, leading=14, textColor=C_GRAY)

    def _add_cover(self, verdict_data: dict[str, Any]) -> None:
        verdict = str(verdict_data.get("verdict") or "IMPROVE")
        score = _safe_score(verdict_data.get("overall_score"))
        risk = str(verdict_data.get("risk_level") or "MEDIUM")

        self.story.append(Spacer(1, 2.7 * cm))
        self.story.append(Paragraph("YOWON AI", self.cover_title))
        self.story.append(Paragraph("Autonomous AI Jury Platform", self.center))
        self.story.append(Spacer(1, 0.45 * cm))
        self.story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER))
        self.story.append(Spacer(1, 0.55 * cm))
        self.story.append(Paragraph(f"<font color='{_hex(C_PRIMARY)}' size='18'><b>{escape(self.project_name)}</b></font>", self.center))
        self.story.append(Paragraph(escape(str(verdict_data.get("project_type") or "Hackathon Project")), self.center))
        self.story.append(Spacer(1, 1.5 * cm))

        data = [
            [
                Paragraph(f"<font color='{_hex(_score_color(score))}' size='36'><b>{score:.0f}</b></font>", self.center),
                Paragraph(f"<font color='{_hex(_verdict_color(verdict))}' size='24'><b>{escape(verdict)}</b></font>", self.center),
                Paragraph(f"<font color='{_hex(_risk_color(risk))}' size='20'><b>{escape(risk)}</b></font>", self.center),
            ],
            ["Overall Score", "Deployment Decision", "Risk Level"],
        ]
        table = Table(data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
        table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_LIGHT, colors.white]),
            ("BOX", (0, 0), (-1, -1), 1, C_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.9 * cm))
        self.story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%B %d, %Y %H:%M UTC')}", self.center))
        self.story.append(PageBreak())

    def _coerce_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, dict):
            return self._mapping_to_text(content)
        if isinstance(content, list):
            return "\n".join(str(item) for item in _normalize_list(content))
        text = str(content)
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return self._mapping_to_text(parsed)
            except Exception:
                pass
        return text

    def _mapping_to_text(self, data: dict[str, Any]) -> str:
        lines: list[str] = []
        for key, value in data.items():
            if key in INTERNAL_REPORT_KEYS:
                continue
            label = key.replace("_", " ").title()
            lines.append(f"{label}:")
            if isinstance(value, (list, tuple)):
                items = _normalize_list(value, fallback=["None evidenced."])
                lines.extend(f"- {item}" for item in items)
            elif isinstance(value, dict):
                public = {k: v for k, v in value.items() if k not in INTERNAL_REPORT_KEYS}
                lines.extend(f"- {k.replace('_', ' ').title()}: {v}" for k, v in public.items()) if public else lines.append("- None evidenced.")
            else:
                lines.append(str(value) if value is not None and str(value).strip() else "None evidenced.")
            lines.append("")
        return "\n".join(lines).strip()

    def _clean_lines(self, content: Any) -> list[str]:
        return _normalize_list(self._coerce_content(content), fallback=[])

    @staticmethod
    def _format_fixes(fixes: list[Any]) -> str:
        lines: list[str] = []
        for i, item in enumerate(fixes):
            if isinstance(item, dict):
                priority = item.get("priority", i + 1)
                fix = item.get("fix") or item.get("step") or item.get("action") or str(item)
                effort = item.get("effort", "TBD")
                lines.append(f"#{priority}: {fix} [Effort: {effort}]")
            else:
                lines.append(f"#{i + 1}: {item}")
        return "\n".join(lines)

    def _add_section(self, title: str, content: Any, color: Any = C_PRIMARY, *, empty_text: str = "No evidence available.") -> None:
        self.story.append(Spacer(1, 0.35 * cm))
        self.story.append(Paragraph(escape(title), self.h2))
        self.story.append(HRFlowable(width="100%", thickness=0.5, color=color))
        self.story.append(Spacer(1, 0.15 * cm))
        lines = self._clean_lines(content)
        if not lines:
            lines = [empty_text]
        for line in lines[:18]:
            is_bullet = bool(re.match(r"^([-*+]|[0-9]+[.)])\s+", line))
            text = re.sub(r"^([-*+]|[0-9]+[.)])\s+", "", line).strip()
            prefix = "- " if is_bullet else ""
            self.story.append(Paragraph(prefix + escape(text), self.bullet if is_bullet else self.body))
        self.story.append(Spacer(1, 0.25 * cm))

    def _add_bullet_list(self, title: str, items: Any, color: Any = C_PRIMARY, *, fallback: list[str] | None = None, numbered: bool = False) -> None:
        clean = _normalize_list(items, fallback=fallback or ["None evidenced."])
        self.story.append(Spacer(1, 0.35 * cm))
        self.story.append(Paragraph(escape(title), self.h2))
        self.story.append(HRFlowable(width="100%", thickness=0.5, color=color))
        self.story.append(Spacer(1, 0.15 * cm))
        for index, item in enumerate(clean[:12], start=1):
            prefix = f"{index}. " if numbered else "- "
            self.story.append(Paragraph(prefix + escape(item), self.bullet))
        self.story.append(Spacer(1, 0.25 * cm))

    def _add_key_value_table(self, title: str, rows: list[tuple[str, Any]], color: Any = C_PRIMARY) -> None:
        self.story.append(Spacer(1, 0.35 * cm))
        self.story.append(Paragraph(escape(title), self.h2))
        self.story.append(HRFlowable(width="100%", thickness=0.5, color=color))
        self.story.append(Spacer(1, 0.18 * cm))
        data: list[list[Any]] = [["Item", "Value"]]
        for key, value in rows:
            data.append([Paragraph(escape(str(key)), self.table_cell), Paragraph(escape(str(value)), self.table_cell)])
        table = Table(data, colWidths=[6 * cm, 9.5 * cm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT]),
            ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.3 * cm))

    def _score_dimensions(self, scores: dict[str, Any]) -> list[str]:
        expected = ["technical", "security", "scalability", "innovation", "impact"]
        if "presentation" in scores:
            expected.insert(4, "presentation")
        return expected

    def _add_score_table(self, scores: dict[str, Any]) -> None:
        self.story.append(Spacer(1, 0.35 * cm))
        self.story.append(Paragraph("Score Table", self.h2))
        self.story.append(HRFlowable(width="100%", thickness=0.5, color=C_PRIMARY))
        self.story.append(Spacer(1, 0.18 * cm))
        labels = {
            "technical": "Forge",
            "security": "Sentinel",
            "scalability": "Scale",
            "innovation": "Visionary",
            "presentation": "Showcase",
            "impact": "Guardian",
        }
        rows: list[list[Any]] = [["Category", "Score", "Grade"]]
        for name in self._score_dimensions(scores):
            score = _safe_score(scores.get(name))
            grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D" if score >= 35 else "F"
            rows.append([
                labels.get(name, name.title()),
                Paragraph(f"<font color='{_hex(_score_color(score))}'><b>{score:.0f}/100</b></font>", self.table_cell),
                Paragraph(f"<font color='{_hex(_score_color(score))}'><b>{grade}</b></font>", self.table_cell),
            ])
        table = Table(rows, colWidths=[7.5 * cm, 4.5 * cm, 3.5 * cm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT]),
            ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.3 * cm))

    def _add_score_chart(self, scores: dict[str, Any]) -> None:
        label_map = {
            "technical": "Forge",
            "security": "Sentinel",
            "scalability": "Scale",
            "innovation": "Visionary",
            "presentation": "Showcase",
            "impact": "Guardian",
        }
        keys = self._score_dimensions(scores)
        labels = [label_map[key] for key in keys]
        values = [_safe_score(scores.get(key)) for key in keys]
        if not any(values):
            values = [0, 0, 0, 0, 0, 0]
        try:
            self.story.append(Spacer(1, 0.35 * cm))
            self.story.append(Paragraph("Category Score Chart", self.h2))
            self.story.append(HRFlowable(width="100%", thickness=0.5, color=C_PRIMARY))
            drawing = Drawing(460, 210)
            chart = VerticalBarChart()
            chart.x = 35
            chart.y = 35
            chart.height = 135
            chart.width = 390
            chart.data = [values]
            chart.valueAxis.valueMin = 0
            chart.valueAxis.valueMax = 100
            chart.valueAxis.valueStep = 20
            chart.categoryAxis.categoryNames = labels
            chart.bars[0].fillColor = C_PRIMARY
            drawing.add(chart)
            drawing.add(String(35, 185, "Scores by evaluation category", fontSize=8, fillColor=C_GRAY))
            self.story.append(drawing)
            self.story.append(Spacer(1, 0.25 * cm))
        except Exception:
            self._add_section("Category Score Chart", "Chart unavailable; score table included above.", C_PRIMARY)

    def _add_radar_chart(self, scores: dict[str, Any]) -> None:
        label_map = {
            "technical": "Forge",
            "security": "Sentinel",
            "scalability": "Scale",
            "innovation": "Visionary",
            "presentation": "Showcase",
            "impact": "Guardian",
        }
        keys = self._score_dimensions(scores)
        labels = [label_map[key] for key in keys]
        values = [_safe_score(scores.get(key)) for key in keys]
        try:
            self.story.append(Spacer(1, 0.35 * cm))
            self.story.append(Paragraph("Radar Chart", self.h2))
            self.story.append(HRFlowable(width="100%", thickness=0.5, color=C_ACCENT))
            drawing = Drawing(460, 240)
            cx, cy, radius = 230, 118, 82
            for ring in (25, 50, 75, 100):
                r = radius * ring / 100
                points: list[float] = []
                for index in range(len(keys)):
                    angle = -math.pi / 2 + index * 2 * math.pi / len(keys)
                    points.extend([cx + math.cos(angle) * r, cy + math.sin(angle) * r])
                drawing.add(Polygon(points, strokeColor=C_BORDER, fillColor=None, strokeWidth=0.5))
            value_points: list[float] = []
            for index, value in enumerate(values):
                angle = -math.pi / 2 + index * 2 * math.pi / len(keys)
                drawing.add(Line(cx, cy, cx + math.cos(angle) * radius, cy + math.sin(angle) * radius, strokeColor=C_BORDER, strokeWidth=0.4))
                lx = cx + math.cos(angle) * (radius + 38)
                ly = cy + math.sin(angle) * (radius + 18)
                drawing.add(String(lx - 28, ly, labels[index], fontSize=7, fillColor=C_GRAY))
                value_points.extend([cx + math.cos(angle) * radius * value / 100, cy + math.sin(angle) * radius * value / 100])
            drawing.add(Polygon(value_points, strokeColor=C_ACCENT, fillColor=colors.Color(0.49, 0.23, 0.93, alpha=0.18), strokeWidth=1.5))
            drawing.add(Circle(cx, cy, 2, fillColor=C_ACCENT, strokeColor=C_ACCENT))
            drawing.add(String(35, 220, "Radar profile of calibrated specialist scores", fontSize=8, fillColor=C_GRAY))
            self.story.append(drawing)
            self.story.append(Spacer(1, 0.25 * cm))
        except Exception:
            self._add_section("Radar Chart", "Radar visualization unavailable; score table included above.", C_ACCENT)

    def _add_risk_visualization(self, verdict_data: dict[str, Any]) -> None:
        risk = str(verdict_data.get("risk_level") or "MEDIUM").upper()
        score = _safe_score(verdict_data.get("overall_score"))
        risk_value = {"LOW": 20, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 95}.get(risk, max(0, 100 - score))
        rows = [
            ("Security Risk", risk, risk_value),
            ("Evidence Gaps", len(_normalize_list(verdict_data.get("missing_evidence"), fallback=[])), min(100, len(_normalize_list(verdict_data.get("missing_evidence"), fallback=[])) * 12)),
            ("Deployment Readiness", f"{score:.0f}/100", max(0, 100 - score)),
        ]
        self.story.append(Spacer(1, 0.35 * cm))
        self.story.append(Paragraph("Risk Visualization", self.h2))
        self.story.append(HRFlowable(width="100%", thickness=0.5, color=C_RED))
        data: list[list[Any]] = [["Risk Area", "Signal", "Risk Level"]]
        for label, signal, value in rows:
            bar = "|" * max(1, round(float(value) / 10))
            data.append([
                Paragraph(escape(str(label)), self.table_cell),
                Paragraph(escape(str(signal)), self.table_cell),
                Paragraph(f"<font color='{_hex(_score_color(100 - float(value)))}'>{escape(bar)}</font>", self.table_cell),
            ])
        table = Table(data, colWidths=[5 * cm, 4 * cm, 6 * cm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT]),
            ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.3 * cm))

    def _add_failure_predictions(self, content: Any) -> None:
        self._add_bullet_list("Top Failure Predictions", content, C_RED, fallback=["No specific failure predictions available."], numbered=True)

    def _build_doc(self, story: list[Any], filename: Path | None = None) -> None:
        doc = SimpleDocTemplate(
            str(filename or self.filename),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        doc.build(story)

    def _fallback_story(self, verdict_data: dict[str, Any], error: Exception) -> list[Any]:
        fallback_story = [
            Paragraph("YOWON AI", self.cover_title),
            Paragraph("Autonomous AI Jury Platform", self.center),
            Spacer(1, 0.4 * cm),
            Paragraph("Executive Summary", self.h1),
            Paragraph(escape(str(verdict_data.get("executive_summary") or "Report generated with fallback layout.")), self.body),
            Paragraph("Final Verdict", self.h1),
            Paragraph(escape(f"{verdict_data.get('verdict', 'IMPROVE')} - {verdict_data.get('overall_score', 0)}/100"), self.body),
            Paragraph(escape(f"Rich PDF layout failed safely: {error}"), self.body),
        ]
        return fallback_story

    def build(self, evaluation_results: dict[str, Any]) -> str:
        verdict_data = dict(evaluation_results.get("verdict") or {})
        agent_scores = verdict_data.get("agent_scores") or {}
        presentation_enabled = _presentation_enabled_from_verdict(verdict_data)
        roadmap = _normalize_list(
            verdict_data.get("roadmap") or verdict_data.get("deployment_roadmap"),
            fallback=DEFAULT_ROADMAP,
        )
        missing_evidence = _normalize_list(verdict_data.get("missing_evidence"), fallback=DEFAULT_MISSING_EVIDENCE)
        positive_factors = _normalize_list(verdict_data.get("positive_factors") or verdict_data.get("positive_highlights"), fallback=DEFAULT_POSITIVE_FACTORS)
        strengths = _normalize_list(verdict_data.get("top_strengths"), fallback=positive_factors)
        weaknesses = _normalize_list(verdict_data.get("top_weaknesses"), fallback=missing_evidence)

        self._add_cover(verdict_data)
        self.story.append(Paragraph("Executive Summary", self.h1))
        self._add_section("Overview", verdict_data.get("executive_summary") or "YOWON AI completed the project intelligence evaluation.", C_PRIMARY)
        context_rows = [
            ("Selected Project Type", verdict_data.get("submitted_project_type") or verdict_data.get("project_type", "Hackathon Project")),
            ("AI Detected Type", (
                f"{verdict_data.get('detected_project_type')} "
                f"({round(float(verdict_data.get('detected_project_confidence') or 0) * 100)}% confidence)"
                if verdict_data.get("detected_project_type") else "Not detected"
            )),
            ("Scoring Rubric Used", verdict_data.get("project_type", "Hackathon Project")),
            ("Evaluation Standard", verdict_data.get("evaluation_standard", "YOWON AI readiness rubric")),
            ("Score Band", verdict_data.get("score_band", "Unknown")),
            ("Confidence", f"{verdict_data.get('confidence', 0)}/100"),
            ("Evidence Quality", verdict_data.get("evidence_quality", "Unknown")),
            ("Repository Completeness", f"{verdict_data.get('repository_completeness_score', 0)}/100"),
        ]
        if "status" in verdict_data:
            context_rows.append(("Evaluation Status", str(verdict_data["status"])))
        if "final_reason" in verdict_data:
            context_rows.append(("Rejection Reason", str(verdict_data["final_reason"])))
        self._add_key_value_table("Evaluation Context", context_rows)
        if verdict_data.get("repository_statistics"):
            self._add_key_value_table(
                "Repository Statistics",
                [(key.replace("_", " ").title(), value) for key, value in verdict_data.get("repository_statistics", {}).items()],
            )
        self._add_score_table(agent_scores)
        self._add_score_chart(agent_scores)
        self._add_radar_chart(agent_scores)
        self._add_risk_visualization(verdict_data)
        self._add_bullet_list("Strengths", strengths, C_GREEN, fallback=DEFAULT_POSITIVE_FACTORS)
        self._add_bullet_list("Weaknesses", weaknesses, C_RED, fallback=DEFAULT_MISSING_EVIDENCE)
        self._add_bullet_list("Positive Factors", positive_factors, C_GREEN, fallback=DEFAULT_POSITIVE_FACTORS)
        self._add_bullet_list("Missing Evidence", missing_evidence, C_RED, fallback=DEFAULT_MISSING_EVIDENCE)
        self._add_bullet_list("Deployment Roadmap", roadmap, C_PRIMARY, fallback=DEFAULT_ROADMAP, numbered=True)
        if verdict_data.get("architecture_summary"):
            self._add_section("Architecture Summary", verdict_data.get("architecture_summary"), C_ACCENT)
        if verdict_data.get("detected_technologies"):
            self._add_bullet_list("Detected Technologies", verdict_data.get("detected_technologies"), C_PRIMARY)
        if verdict_data.get("detected_algorithms"):
            self._add_bullet_list("Detected Algorithms", verdict_data.get("detected_algorithms"), C_GREEN)
        if verdict_data.get("evidence_found") or verdict_data.get("evidence_missing"):
            self._add_bullet_list("Evidence Found", verdict_data.get("evidence_found"), C_GREEN, fallback=["No implementation evidence found."])
            self._add_bullet_list("Evidence Missing", verdict_data.get("evidence_missing"), C_RED, fallback=["No missing implementation evidence recorded."])
        for title, key, color in (
            ("REST APIs Found", "rest_apis_found", C_PRIMARY),
            ("Database Usage", "database_usage", C_ACCENT),
            ("Authentication Usage", "authentication_usage", C_YELLOW),
            ("Integrations", "integrations", C_GREEN),
        ):
            if verdict_data.get(key):
                self._add_bullet_list(title, verdict_data.get(key), color)
        if verdict_data.get("top_code_snippets"):
            snippet_lines = [
                f"{item.get('path')}: {str(item.get('snippet') or '').replace(chr(10), ' ')[:350]}"
                for item in verdict_data.get("top_code_snippets", [])[:5]
                if isinstance(item, dict)
            ]
            self._add_bullet_list("Technical Evidence Summary", snippet_lines, C_ACCENT, fallback=["No code snippets available."])
        if verdict_data.get("project_type_justification"):
            self._add_section("Project Type Justification", verdict_data.get("project_type_justification"), C_ACCENT)
        if verdict_data.get("calibration_explanation"):
            self._add_section("Calibration Explanation", verdict_data.get("calibration_explanation"), C_YELLOW)

        if verdict_data.get("confidence_sources"):
            self._add_bullet_list("Confidence Sources", verdict_data.get("confidence_sources"), C_GREEN)
        if verdict_data.get("penalties"):
            penalties = [
                f"{item.get('dimension', 'overall')}: {item.get('factor')}"
                for item in verdict_data.get("penalties", [])
                if isinstance(item, dict)
            ]
            self._add_bullet_list("Penalties", penalties, C_YELLOW, fallback=["No score penalties recorded."])

        self.story.append(PageBreak())
        self.story.append(Paragraph("Detailed Findings", self.h1))
        detailed_sections = [
            ("Forge Analysis", "technical", C_PRIMARY),
            ("Sentinel Analysis", "security", C_RED),
            ("Visionary Assessment", "innovation", C_PRIMARY),
            ("Guardian Impact Analysis", "impact", C_YELLOW),
            ("Failure Predictions", "failure", C_RED),
            ("Scalability Assessment", "scalability", C_PRIMARY),
            ("Cross Examination Results", "cross_exam", C_PRIMARY),
        ]
        if presentation_enabled:
            detailed_sections.insert(-1, ("Showcase Review", "ppt", C_PRIMARY))
        for title, key, color in detailed_sections:
            if key == "failure":
                self._add_failure_predictions(evaluation_results.get(key))
            else:
                self._add_section(title, evaluation_results.get(key), color)

        self.story.append(PageBreak())
        self.story.append(Paragraph("Final Verdict", self.h1))
        self._add_bullet_list("Blocking Issues", verdict_data.get("blocking_issues"), C_RED, fallback=["No blocking issues recorded."])
        self._add_bullet_list("Recommended Fixes", verdict_data.get("recommended_fixes"), C_YELLOW, fallback=DEFAULT_ROADMAP[:3], numbered=True)
        self._add_bullet_list("Deployment Roadmap", roadmap, C_PRIMARY, fallback=DEFAULT_ROADMAP, numbered=True)
        self._add_section(
            "Deployment Decision",
            f"Verdict: {verdict_data.get('verdict', 'IMPROVE')}\nOverall Score: {verdict_data.get('overall_score', 0)}/100\nRisk Level: {verdict_data.get('risk_level', 'MEDIUM')}",
            _verdict_color(str(verdict_data.get("verdict") or "IMPROVE")),
        )

        tmp_path = self.filename.with_suffix(".tmp")
        for candidate in (tmp_path, self.filename):
            try:
                if candidate.exists():
                    candidate.unlink()
            except OSError:
                pass

        logger.info("[PDF] Generation started report_id=%s project=%s", self.report_id, self.project_name)
        try:
            try:
                self._build_doc(self.story, tmp_path)
            except Exception as exc:
                logger.exception("[PDF] Rich ReportLab layout failed report_id=%s", self.report_id)
                self._build_doc(self._fallback_story(verdict_data, exc), tmp_path)

            size = validate_pdf_file(tmp_path)
            logger.info("[PDF] File size report_id=%s bytes=%d", self.report_id, size)
            os.replace(tmp_path, self.filename)
            size = validate_pdf_file(self.filename)
            logger.info("[PDF] Validation passed report_id=%s bytes=%d", self.report_id, size)
            logger.info("[PDF] Generation completed report_id=%s path=%s", self.report_id, self.filename)
        except Exception as exc:
            for candidate in (tmp_path, self.filename):
                try:
                    if candidate.exists():
                        candidate.unlink()
                except OSError:
                    pass
            if isinstance(exc, PDFGenerationError):
                raise
            raise PDFGenerationError(str(exc)) from exc
        return str(self.filename)


def generate_report(project_name: str, report_id: str, evaluation_results: dict[str, Any]) -> str:
    """Generate a YOWON AI PDF report and return its path."""
    return YowonReport(project_name=project_name, report_id=report_id).build(evaluation_results or {})
