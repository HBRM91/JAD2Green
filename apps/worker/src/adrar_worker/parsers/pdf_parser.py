"""
Clean PDF parser using pdfplumber.

Extracts tables from PDFs with embedded text. For scanned images (low text density),
callers should route to scan_parser instead — see is_scan() for the routing test.
"""

from __future__ import annotations

import io

import pdfplumber

from .base import ExtractedFact
from .xlsx_parser import _rows_to_facts

_SCAN_THRESHOLD_CHARS_PER_PAGE = 50


def is_scan(content: bytes) -> bool:
    """Return True if the PDF appears to be a scanned image (very low text density)."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if not pdf.pages:
                return True
            total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
            return (total_chars / len(pdf.pages)) < _SCAN_THRESHOLD_CHARS_PER_PAGE
    except Exception:
        return True  # treat unreadable PDFs as scans


def parse_pdf(content: bytes, doc_id: str, filename: str) -> list[ExtractedFact]:
    """Extract tables from a clean (text-based) PDF."""
    facts: list[ExtractedFact] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                for table in page.extract_tables() or []:
                    if not table or not table[0]:
                        continue
                    headers = [str(c).strip() if c else "" for c in table[0]]
                    data_rows = [list(row) for row in table[1:]]
                    page_facts = _rows_to_facts(
                        headers, data_rows, doc_id, filename, page=page_num + 1
                    )
                    # Add bbox from page for provenance
                    for f in page_facts:
                        f.source_page = page_num + 1
                    facts.extend(page_facts)
    except Exception:
        pass  # pdfplumber failure → return empty (caller may re-route to scan)
    return facts
