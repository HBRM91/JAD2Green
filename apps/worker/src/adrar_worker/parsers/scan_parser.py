"""
Messy multilingual scan parser using Claude Haiku.

Haiku is invoked ONLY for low-text-density PDFs (scanned images) when an
ANTHROPIC_API_KEY is configured. If not configured, returns empty list with
a note in the processing log.

INVARIANT: Haiku extracts RAW TEXT → proposed facts only.
           Haiku NEVER computes emissions. The kernel is never called here.
           (§0 inv 1: LLM never touches the calc path)
"""

from __future__ import annotations

import base64
import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation

from .base import ExtractedFact

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """\
You are a data extractor for GHG emission reporting.
Extract energy/fuel consumption data from the provided document image.
Return ONLY a JSON array. Each element must have:
  category (string, e.g. scope1_mobile, scope1_stationary, scope2_electricity, scope3_transport),
  activity_value (number),
  activity_unit (string, e.g. kWh, L, MJ, kg, m3, km),
  period_start (YYYY-MM-DD),
  period_end (YYYY-MM-DD),
  scope (integer 1, 2, or 3),
  confidence (float 0.0–1.0),
  fuel_type (string or null),
  raw_text (the exact text you read).
Do NOT compute emissions. Do NOT include calculated totals. Extract raw data only."""


def _parse_haiku_response(json_text: str, doc_id: str, filename: str) -> list[ExtractedFact]:
    try:
        items = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return []

    facts: list[ExtractedFact] = []
    for item in items if isinstance(items, list) else []:
        try:
            value = Decimal(str(item.get("activity_value", 0)))
            if value <= 0:
                continue
            facts.append(
                ExtractedFact(
                    category=str(item.get("category", "scope1_stationary")),
                    activity_value=value,
                    activity_unit=str(item.get("activity_unit", "unknown")),
                    period_start=date.fromisoformat(item.get("period_start", "2024-01-01")),
                    period_end=date.fromisoformat(item.get("period_end", "2024-12-31")),
                    scope=int(item.get("scope", 1)),
                    fuel_type=item.get("fuel_type"),
                    confidence=float(item.get("confidence", 0.7)),
                    raw_text=item.get("raw_text"),
                )
            )
        except (KeyError, ValueError, InvalidOperation):
            continue
    return facts


def parse_scan(content: bytes, doc_id: str, filename: str) -> list[ExtractedFact]:
    """
    Extract activity data from a scanned PDF using Haiku.

    If ANTHROPIC_API_KEY is not set, returns empty list (callers log the skip).
    This ensures tests without credentials still work.

    LLM invariant: output goes to propose_activity only — kernel is never called here.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return []  # graceful degradation; logged by caller

    try:
        import anthropic

        b64_pdf = base64.standard_b64encode(content).decode()
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": b64_pdf,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract all energy/fuel consumption data as JSON.",
                        },
                    ],
                }
            ],
        )
        raw = msg.content[0].text if msg.content else "[]"
        # Extract JSON block if wrapped in markdown
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return _parse_haiku_response(raw, doc_id, filename)
    except Exception:
        return []
