"""
Messy multilingual scan parser.

PaddleOCR-VL-1.5 via Aliyun DashScope converts the raw PDF into text + bbox
+ per-page confidence. Qwen3-Plus via OpenRouter then converts the OCR text
into structured activity facts. Both providers are called only when their
respective env keys are configured; if absent, returns empty list and the
caller logs the skip.

INVARIANT: LLM/OCR extracts RAW TEXT → proposed facts only. Neither ever
           computes emissions. The kernel is never called here.
           (§0 inv 1: LLM never touches the calc path)
"""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation

from .aliyun_dashscope import ocr_scan
from .base import ExtractedFact

_EXTRACTION_PROMPT = """\
Tu es un extracteur de données pour un bilan carbone marocain.
À partir du texte OCR ci-dessous (document scanné, possiblement FR/AR/EN),
extrais chaque consommation d'énergie ou de carburant sous forme JSON.

Retourne UNIQUEMENT un tableau JSON. Chaque élément doit avoir :
  category (chaîne, ex. scope1_mobile, scope1_stationary, scope2_electricity, scope3_transport),
  activity_value (nombre),
  activity_unit (chaîne, ex. kWh, L, MJ, kg, m3, km, tonne),
  period_start (YYYY-MM-DD),
  period_end (YYYY-MM-DD),
  scope (entier 1, 2 ou 3),
  confidence (flottant 0.0–1.0),
  fuel_type (chaîne ou null),
  raw_text (le texte exact lu).
Ne calcule AUCUNE émission. Ne fais AUCUN total. Extrait les données brutes uniquement.

TEXTE OCR :
"""


def _parse_qwen_response(json_text: str, doc_id: str, filename: str) -> list[ExtractedFact]:
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


def _extract_facts_with_qwen(ocr_text: str) -> list[ExtractedFact]:
    """Qwen3-Plus via OpenRouter: OCR text → structured activity facts."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return []

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://adrar.ai",
            "X-Title": "Adrar AI — Bilan Carbone",
        },
    )
    model = os.getenv("EXTRACTION_MODEL", "qwen/qwen3-plus")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _EXTRACTION_PROMPT + ocr_text}],
            max_tokens=2048,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or "[]"
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return _parse_qwen_response(raw, "", "")
    except Exception:
        return []


def parse_scan(content: bytes, doc_id: str, filename: str) -> list[ExtractedFact]:
    """
    Extract activity data from a scanned PDF.

    Pipeline: PaddleOCR-VL-1.5 (DashScope) → Qwen3-Plus (OpenRouter).
    If DASHSCOPE_API_KEY or OPENROUTER_API_KEY is not set, the corresponding
    stage is skipped (graceful degradation; caller logs the skip).

    LLM invariant: output goes to propose_activity only — kernel is never called.
    """
    if not os.getenv("DASHSCOPE_API_KEY"):
        return []
    ocr_text = ocr_scan(content)
    if not ocr_text:
        return []
    return _extract_facts_with_qwen(ocr_text)
