"""
LLM narrative generation for Bilan Carbone report.

ARCHITECTURE BOUNDARY (§0 invariants):
  - Input: snapshot AGGREGATE totals only (no raw activity_facts, no documents)
  - Output: human-readable narrative sections
  - LLM is NEVER in the calc path — kernel is never called here

Provider selection via NARRATIVE_MODEL env var (default: deepseek-chat-v3).
Chinese primary, Gemini 2.5 Flash Lite as cheap last-resort cost option. No
Anthropic in the cascade (dropped per TODOLIST Phase 1).

Cascade (tried in order if primary fails):
  deepseek-chat-v3  (OpenRouter — cheapest, good French)
  qwen3-plus        (OpenRouter — best French)
  glm-4-plus        (OpenRouter — cheap last-resort)
  gemini-2.5-flash-lite (Google — cost safety net)

§0.12: The generated report always includes an AI transparency disclosure.
"""

from __future__ import annotations

import json
import os
import time
from decimal import Decimal

# ---------------------------------------------------------------------------
# §0.12 — AI transparency disclosure. Always present. Non-negotiable.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Stub — returned when no API key is configured (offline / test mode)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------
# Maps NARRATIVE_MODEL value → (api_key_env, model_id, call_fn)
# call_fn is resolved lazily at runtime to avoid hard import errors when
# a provider's SDK is not installed.
# Chinese primary per TODOLIST Phase 1 ("fully-Chinese provider swap").
# Gemini 2.5 Flash Lite kept as cheap last-resort cost option (free tier).

_PROVIDER_CONFIGS: dict[str, dict] = {
    # ── DeepSeek V3 via OpenRouter (default — cheapest, good French) ───────
    "deepseek-chat-v3": {
        "key_env": "OPENROUTER_API_KEY",
        "model": "deepseek/deepseek-chat-v3",
        "backend": "openrouter",
    },
    # ── Qwen3-Plus via OpenRouter (best French quality) ────────────────────
    "qwen3-plus": {
        "key_env": "OPENROUTER_API_KEY",
        "model": "qwen/qwen3-plus",
        "backend": "openrouter",
    },
    # ── GLM-4-Plus via OpenRouter (Zhipu — cheap last-resort) ──────────────
    "glm-4-plus": {
        "key_env": "OPENROUTER_API_KEY",
        "model": "zhipu/glm-4-plus",
        "backend": "openrouter",
    },
    # ── Google Gemini 2.5 Flash Lite (cost safety net, free tier) ──────────
    "gemini-2.5-flash-lite": {
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash-lite",
        "backend": "gemini",
    },
}

# Fallback chain — tried in order if primary fails
_FALLBACK_CHAIN = [
    "deepseek-chat-v3",
    "qwen3-plus",
    "glm-4-plus",
    "gemini-2.5-flash-lite",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_float(val) -> float:
    try:
        return float(Decimal(str(val)))
    except Exception:
        return 0.0


def _build_prompt(
    totals: dict,
    project_name: str,
    reporting_year: int,
    methodology_name: str,
    gwp_basis: str,
    gri_305_data: dict | None,
    ndc_alignment: dict | None,
    sector_code: str | None,
    reporting_frameworks: list[str] | None,
) -> str:
    scope1 = _to_float(totals.get("scope1", 0))
    scope2_loc = _to_float(totals.get("scope2_location", 0))
    scope2_mkt = _to_float(totals.get("scope2_market", 0))
    scope3 = _to_float(totals.get("scope3", 0))
    total = _to_float(totals.get("total", 0))

    morocco_ctx = ""
    if ndc_alignment and ndc_alignment.get("progress_pct") is not None:
        pct = ndc_alignment["progress_pct"]
        target = ndc_alignment.get("target_emissions", 0)
        morocco_ctx += (
            f"\nAlignement NDC Maroc 2030 (objectif -45.5% vs BAU) :\n"
            f"- Progression vers l'objectif : {pct:.1f}%\n"
            f"- Cible NDC : {_to_float(target):.2f} tCO₂e\n"
            f"- En bonne voie : {'Oui' if ndc_alignment.get('on_track') else 'Non'}\n"
        )
    if gri_305_data:
        morocco_ctx += (
            f"\nDivulgations GRI 305 :\n"
            f"- GRI 305-1 (Scope 1) : {_to_float(gri_305_data.get('305-1', 0)):.2f} tCO₂e\n"
            f"- GRI 305-2 loc. (Scope 2) : {_to_float(gri_305_data.get('305-2-loc', 0)):.2f} tCO₂e\n"
            f"- GRI 305-3 (Scope 3) : {_to_float(gri_305_data.get('305-3', 0)):.2f} tCO₂e\n"
        )
    if reporting_frameworks:
        morocco_ctx += f"\nRéférentiels applicables : {', '.join(reporting_frameworks)}\n"
    if sector_code:
        morocco_ctx += f"Secteur (code) : {sector_code}\n"

    return f"""\
Tu es un expert Bilan Carbone marocain certifié. Rédige en français professionnel \
un rapport structuré basé UNIQUEMENT sur les données agrégées ci-dessous.

Projet : {project_name}
Année de référence : {reporting_year}
Méthode : {methodology_name} (base GWP : {gwp_basis})

Résultats agrégés (tCO₂e) :
- Scope 1 (émissions directes) : {scope1:.2f}
- Scope 2 location-based : {scope2_loc:.2f}
- Scope 2 market-based : {scope2_mkt:.2f}
- Scope 3 (indirect) : {scope3:.2f}
- Total (S1 + S2 location + S3) : {total:.2f}
{morocco_ctx}
Contexte réglementaire marocain à mentionner si pertinent :
- Loi 99-12 portant Charte de l'Environnement et du Développement Durable
- Loi 47-09 sur l'efficacité énergétique (AMEE)
- NDC Maroc 2021 : -45.5% d'ici 2030 vs BAU (conditionnel)
- SNDD 2030 : Stratégie Nationale de Développement Durable
- Rapport RSE Bourse de Casablanca (BVC) — obligatoire pour sociétés cotées
- Facteur ONEE 2023 : 0.679 kgCO₂e/kWh

Retourne UNIQUEMENT du JSON valide (sans balises markdown) :
{{
  "exec_summary": "paragraphe de synthèse (4-5 phrases, contexte réglementaire marocain)",
  "key_findings": ["constat 1", "constat 2", "constat 3", "constat 4"],
  "recommendations": ["priorité Scope 1", "recommandation 2", "lien NDC/réglementaire"]
}}"""


def _parse_response(raw: str) -> dict:
    """Extract JSON from LLM response, stripping markdown fences if present."""
    text = raw.strip()
    if "```" in text:
        # strip ```json ... ``` or ``` ... ```
        parts = text.split("```")
        for part in parts:
            cleaned = part.lstrip("json").strip()
            if cleaned.startswith("{"):
                text = cleaned
                break
    # Find first { ... } block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


# ---------------------------------------------------------------------------
# Backend call implementations
# ---------------------------------------------------------------------------

def _call_gemini(model: str, api_key: str, prompt: str) -> dict:
    import google.generativeai as genai  # type: ignore
    genai.configure(api_key=api_key)
    client = genai.GenerativeModel(model)
    response = client.generate_content(
        prompt,
        generation_config={"temperature": 0.3, "max_output_tokens": 1200},
    )
    return _parse_response(response.text)


def _call_openrouter(model: str, api_key: str, prompt: str) -> dict:
    """OpenRouter uses OpenAI-compatible API — works for Qwen and DeepSeek."""
    from openai import OpenAI  # type: ignore
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://adrar.ai",
            "X-Title": "Adrar AI — Bilan Carbone",
        },
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.3,
    )
    return _parse_response(response.choices[0].message.content or "")


_BACKEND_CALLS = {
    "gemini": _call_gemini,
    "openrouter": _call_openrouter,
}


# ---------------------------------------------------------------------------
# Provider resolution + fallback logic
# ---------------------------------------------------------------------------

def _try_provider(provider_key: str, prompt: str) -> dict | None:
    """
    Attempt to call a single provider. Returns parsed dict on success,
    None on any failure (missing key, network error, parse error).
    """
    cfg = _PROVIDER_CONFIGS.get(provider_key)
    if not cfg:
        return None

    api_key = os.getenv(cfg["key_env"], "")
    if not api_key:
        return None

    backend_fn = _BACKEND_CALLS.get(cfg["backend"])
    if not backend_fn:
        return None

    try:
        return backend_fn(cfg["model"], api_key, prompt)
    except Exception:
        return None


def _resolve_provider_chain(requested: str) -> list[str]:
    """
    Build the ordered list of providers to try:
    1. Requested provider first
    2. Then the fallback chain (skipping already-tried)
    """
    chain = [requested] if requested in _PROVIDER_CONFIGS else []
    for p in _FALLBACK_CHAIN:
        if p not in chain:
            chain.append(p)
    return chain


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_narrative(
    totals: dict,
    uncertainty: dict,
    project_name: str,
    reporting_year: int,
    methodology_name: str,
    gwp_basis: str,
    gri_305_data: dict | None = None,
    ndc_alignment: dict | None = None,
    sector_code: str | None = None,
    reporting_frameworks: list[str] | None = None,
) -> dict:
    """
    Generate narrative sections using the configured LLM provider.

    Provider is selected via LLM_PROVIDER env var (default: gemini-2.5-flash-lite).
    On failure, automatically tries the fallback chain before returning the stub.

    Input is AGGREGATE data only — no raw facts, no documents (§0.11).
    """
    provider = os.getenv("NARRATIVE_MODEL", "deepseek-chat-v3").strip().lower()
    prompt = _build_prompt(
        totals=totals,
        project_name=project_name,
        reporting_year=reporting_year,
        methodology_name=methodology_name,
        gwp_basis=gwp_basis,
        gri_305_data=gri_305_data,
        ndc_alignment=ndc_alignment,
        sector_code=sector_code,
        reporting_frameworks=reporting_frameworks,
    )

    chain = _resolve_provider_chain(provider)
    last_error: str = ""

    for attempt, p in enumerate(chain):
        cfg = _PROVIDER_CONFIGS.get(p, {})
        api_key = os.getenv(cfg.get("key_env", ""), "")
        if not api_key:
            continue  # skip silently — key not configured

        # Exponential backoff on retry (not first attempt)
        if attempt > 0:
            time.sleep(min(2 ** (attempt - 1), 8))

        result = _try_provider(p, prompt)
        if result is not None:
            # Tag which provider was used (for logging/debugging)
            result["_provider"] = p
            return result

        last_error = p  # noqa: F841

    # All providers failed — return stub with note
    stub = dict(_STUB_NARRATIVE)
    stub["exec_summary"] = (
        "[Mode hors-ligne — aucun fournisseur LLM disponible]\n"
        + stub["exec_summary"]
    )
    return stub
