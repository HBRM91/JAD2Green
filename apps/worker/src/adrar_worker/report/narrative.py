"""
LLM narrative generation for Bilan Carbone report.

ARCHITECTURE BOUNDARY (§0 invariants):
  - Input: snapshot AGGREGATE totals only (no raw activity_facts, no documents)
  - Output: human-readable narrative sections
  - LLM is NEVER in the calc path — kernel is never called here
  - If ANTHROPIC_API_KEY is not set, returns stub narrative for offline use

§0.12: The generated report always includes an AI transparency disclosure.
"""

from __future__ import annotations

import os
from decimal import Decimal

_MODEL = "claude-haiku-4-5-20251001"

# §0.12 — AI transparency disclosure block. Always present. Non-negotiable.
DISCLOSURE_BLOCK = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVIS DE TRANSPARENCE IA / AI TRANSPARENCY NOTICE

Ce rapport a été élaboré avec l'assistance du système Adrar AI.
Les calculs d'émissions sont déterministes et basés sur les facteurs
d'émission officiels (Base Carbone® ADEME, ONEE) fournis "en l'état".
Les sections narratives (synthèse, recommandations) ont été générées
par intelligence artificielle à partir des agrégats du bilan.

Adrar AI accélère l'expertise des consultants — elle ne la remplace pas.
Ce rapport nécessite la validation d'un expert qualifié avant toute
utilisation officielle, réglementaire ou de conformité.

"AI-assisted drafting. Emission factors require expert validation."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

_STUB_NARRATIVE = {
    "exec_summary": (
        "[Synthèse générée automatiquement — vérification expert requise]\n"
        "Ce bilan carbone présente les émissions de gaz à effet de serre "
        "conformément à la méthode Bilan Carbone® de l'ADEME."
    ),
    "key_findings": [
        "Les émissions totales ont été calculées sur la base des données validées.",
        "Le Scope 2 est présenté en double valeur (location-based et market-based).",
        "L'incertitude associée aux calculs est indiquée séparément des totaux.",
    ],
    "recommendations": [
        "Compléter les données manquantes et valider les hypothèses retenues.",
        "Engager un plan de réduction des émissions Scope 1 en priorité.",
        "Explorer les options de garanties d'origine pour le Scope 2 marché.",
    ],
}


def _to_float(val) -> float:
    try:
        return float(Decimal(str(val)))
    except Exception:
        return 0.0


def generate_narrative(
    totals: dict,
    uncertainty: dict,
    project_name: str,
    reporting_year: int,
    methodology_name: str,
    gwp_basis: str,
) -> dict:
    """
    Call Claude to generate narrative sections.
    Input is AGGREGATE data only — no raw facts, no documents (§0.11).
    Falls back to stub if ANTHROPIC_API_KEY not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return dict(_STUB_NARRATIVE)

    scope1 = _to_float(totals.get("scope1", 0))
    scope2_loc = _to_float(totals.get("scope2_location", 0))
    scope2_mkt = _to_float(totals.get("scope2_market", 0))
    scope3 = _to_float(totals.get("scope3", 0))
    total = _to_float(totals.get("total", 0))

    prompt = f"""\
Tu es un expert Bilan Carbone. Rédige en français un rapport structuré pour :
Projet : {project_name}
Année de référence : {reporting_year}
Méthode : {methodology_name} (base GWP : {gwp_basis})

Résultats agrégés (tCO₂e) :
- Scope 1 (émissions directes) : {scope1:.2f}
- Scope 2 location-based : {scope2_loc:.2f}
- Scope 2 market-based : {scope2_mkt:.2f}
- Scope 3 (indirect) : {scope3:.2f}
- Total (S1 + S2 location + S3) : {total:.2f}

Rédige UNIQUEMENT à partir de ces données agrégées. Retourne JSON avec :
{{
  "exec_summary": "paragraphe de synthèse (3-4 phrases)",
  "key_findings": ["constat 1", "constat 2", "constat 3"],
  "recommendations": ["recommandation 1", "recommandation 2", "recommandation 3"]
}}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        raw = response.content[0].text
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception:
        return dict(_STUB_NARRATIVE)
