"""
tools/pdf_tool.py — PDF text and metadata extractor using PyMuPDF (fitz).

Extracts:
  - Full text per page
  - Section headings (heuristic: large or bold text)
  - Document metadata
  - Image count per page
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from config import MAX_PDF_PAGES


def extract_pdf_data(pdf_path: str | Path) -> dict[str, Any]:
    """
    Parse a PDF file and return structured content.

    Returns:
      {
        "metadata":   dict of PDF metadata fields,
        "page_count": int,
        "pages":      list of {"page": int, "text": str, "image_count": int},
        "full_text":  str  (all pages joined),
        "headings":   list[str]  (heuristic section titles),
      }
    """
    path = Path(pdf_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    result: dict[str, Any] = {
        "metadata": {},
        "page_count": 0,
        "pages": [],
        "full_text": "",
        "headings": [],
    }

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        return {"error": f"Could not open PDF: {exc}"}

    result["metadata"] = {k: v for k, v in doc.metadata.items() if v}
    result["page_count"] = doc.page_count

    all_text_parts: list[str] = []
    headings: list[str] = []

    for page_num, page in enumerate(doc):
        if page_num >= MAX_PDF_PAGES:
            break

        # ── Extract text blocks ───────────────────────────────────────────
        blocks = page.get_text("dict")["blocks"]  # type: ignore[attr-defined]
        page_text_parts: list[str] = []

        for block in blocks:
            if block.get("type") != 0:  # 0 = text block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    page_text_parts.append(text)

                    # Heuristic: font size > 14 or bold flags → heading
                    size = span.get("size", 0)
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 2**4)
                    if size > 14 or (is_bold and size > 11):
                        if len(text) < 120:
                            headings.append(text)

        page_text = " ".join(page_text_parts)
        result["pages"].append({
            "page": page_num + 1,
            "text": page_text,
            "image_count": len(page.get_images()),
        })
        all_text_parts.append(page_text)

    doc.close()

    result["full_text"] = "\n\n".join(all_text_parts)
    result["headings"] = list(dict.fromkeys(headings))  # deduplicate, preserve order
    return result