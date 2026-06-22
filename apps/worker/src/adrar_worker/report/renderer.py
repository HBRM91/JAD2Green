"""
Bilan Carbone DOCX report renderer.

§0.11 — Report is built exclusively from report_snapshot aggregates.
         Raw activity_facts, provenance, and document content are NEVER
         passed to this module.
§0.12 — AI transparency disclosure block is always included.
"""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from .narrative import DISCLOSURE_BLOCK


def _dec(val) -> str:
    """Format Decimal or numeric value as string with 2 dp."""
    try:
        return f"{float(Decimal(str(val))):.2f}"
    except Exception:
        return "0.00"


def _heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _add_png(doc: Document, png_bytes: bytes, width_inches: float = 5.5) -> None:
    doc.add_picture(io.BytesIO(png_bytes), width=Inches(width_inches))


def render_bilan_carbone_docx(
    snapshot: dict,
    project_name: str,
    client_name: str,
    methodology_name: str,
    narrative: dict,
    charts: dict,
) -> bytes:
    """
    Build a Bilan Carbone DOCX report.

    Args:
        snapshot: report_snapshot row (aggregate fields only — §0.11)
        project_name: from projects table
        client_name: from clients table
        methodology_name: from methodologies table
        narrative: {exec_summary, key_findings, recommendations} from LLM
        charts: {scope_pie: bytes, category_bar: bytes, scope2_bar: bytes}

    Returns:
        DOCX file as bytes, ready for download or Google export.
    """
    doc = Document()

    # ── Page margins ─────────────────────────────────────────────────────
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.2)
        section.right_margin = Inches(1.2)

    # ── 1. Title page ─────────────────────────────────────────────────────
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("BILAN CARBONE®")
    run.font.size = Pt(24)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1A, 0x5C, 0x38)

    doc.add_paragraph()
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run("Rapport d'émissions de gaz à effet de serre\n").font.size = Pt(14)
    sub.add_run(f"Projet : {project_name}\n").font.size = Pt(13)
    sub.add_run(f"Client : {client_name}\n").font.size = Pt(12)
    sub.add_run(f"Année de référence : {snapshot.get('reporting_year', '—')}\n").font.size = Pt(12)
    sub.add_run(f"Méthode : {methodology_name}\n").font.size = Pt(12)
    sub.add_run(f"Base GWP : {snapshot.get('gwp_basis', 'AR5')}\n").font.size = Pt(11)
    sub.add_run(
        f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    ).font.size = Pt(10)

    doc.add_page_break()

    # ── 2. AI transparency disclosure (§0.12 — always present) ───────────
    _heading(doc, "Avis de transparence IA", level=1)
    p = doc.add_paragraph(DISCLOSURE_BLOCK)
    p.style.font.size = Pt(9)

    doc.add_page_break()

    # ── 3. Executive summary ──────────────────────────────────────────────
    _heading(doc, "Synthèse exécutive", level=1)
    doc.add_paragraph(narrative.get("exec_summary", ""))

    doc.add_paragraph()
    _heading(doc, "Constats clés", level=2)
    for finding in narrative.get("key_findings", []):
        doc.add_paragraph(finding, style="List Bullet")

    doc.add_page_break()

    # ── 4. Résultats par scope ────────────────────────────────────────────
    _heading(doc, "Résultats des émissions", level=1)
    totals = snapshot.get("totals_co2e", {})
    uncertainty = snapshot.get("uncertainty", {})

    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Scope", "tCO₂e", "Incertitude ±", "Note"]):
        hdr[i].text = h
        hdr[i].paragraphs[0].runs[0].font.bold = True

    def _unc_pct(key: str) -> str:
        u = uncertainty.get(key, {})
        frac = u.get("fraction", "0")
        try:
            return f"{float(Decimal(str(frac))) * 100:.0f}%"
        except Exception:
            return "—"

    rows = [
        ("Scope 1 — Émissions directes", totals.get("scope1", "0"), _unc_pct("scope1"), ""),
        (
            "Scope 2 — Location-based",
            snapshot.get("scope2_location_t") or totals.get("scope2_location", "0"),
            _unc_pct("scope2_location"),
            "Méthode réseau",
        ),
        (
            "Scope 2 — Market-based",
            snapshot.get("scope2_market_t") or totals.get("scope2_market", "0"),
            _unc_pct("scope2_market"),
            "Méthode marché",
        ),
        ("Scope 3 — Indirect", totals.get("scope3", "0"), _unc_pct("scope3"), ""),
        ("TOTAL (S1 + S2 loc + S3)", totals.get("total", "0"), _unc_pct("total"), "Périmètre GHG Protocol"),
    ]
    for label, value, unc, note in rows:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = _dec(value)
        row[2].text = unc
        row[3].text = note

    doc.add_paragraph()

    # ── 5. Charts ─────────────────────────────────────────────────────────
    if charts.get("scope_pie"):
        _heading(doc, "Répartition des émissions", level=2)
        _add_png(doc, charts["scope_pie"], width_inches=4.5)
        doc.add_paragraph()

    if charts.get("scope2_bar"):
        _heading(doc, "Scope 2 : Location vs Marché", level=2)
        _add_png(doc, charts["scope2_bar"], width_inches=4.5)
        doc.add_paragraph()

    if charts.get("category_bar"):
        doc.add_page_break()
        _heading(doc, "Émissions par catégorie", level=2)
        _add_png(doc, charts["category_bar"], width_inches=5.5)
        doc.add_paragraph()

    # ── 6. Recommandations ────────────────────────────────────────────────
    doc.add_page_break()
    _heading(doc, "Recommandations", level=1)
    for rec in narrative.get("recommendations", []):
        doc.add_paragraph(rec, style="List Bullet")

    # ── 7. Annexe : empreinte du calcul ──────────────────────────────────
    doc.add_page_break()
    _heading(doc, "Annexe — Empreinte du calcul", level=1)
    doc.add_paragraph(
        f"Hash d'état (state_hash) : {snapshot.get('state_hash', '—')}\n"
        f"Versions des jeux de facteurs : {', '.join(snapshot.get('factor_set_versions', []))}\n"
        f"Horizon GWP : 100 ans — Base : {snapshot.get('gwp_basis', 'AR5')}\n"
        f"L'incertitude est calculée séparément des totaux conformément aux invariants §0.2."
    )

    # Serialize to bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
