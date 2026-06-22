"""
Base types for document extraction.

ExtractedFact is the common output of every parser.
It is NEVER a validated emission calculation — it is raw extracted data
that becomes a proposed activity_fact (§0 inv 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class ExtractedFact:
    category: str
    activity_value: Decimal
    activity_unit: str
    period_start: date
    period_end: date
    scope: int
    sub_category: str | None = None
    scope2_type: str | None = None
    fuel_type: str | None = None
    confidence: float = 1.0          # 0.0–1.0; goes into provenance
    source_page: int | None = None
    source_bbox: dict | None = None  # {"x0":…,"y0":…,"x1":…,"y1":…}
    raw_text: str | None = None


def build_provenance(
    doc_id: str,
    filename: str,
    fact: ExtractedFact,
    extraction_method: str,
) -> dict:
    """Build the provenance JSONB dict stored on each activity_fact."""
    return {
        "doc_id": doc_id,
        "doc_filename": filename,
        "extraction_method": extraction_method,
        "confidence": fact.confidence,
        "source_page": fact.source_page,
        "source_bbox": fact.source_bbox,
        "raw_text": fact.raw_text,
        "fuel_type": fact.fuel_type,
    }
