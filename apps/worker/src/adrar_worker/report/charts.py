"""
Chart generation for Bilan Carbone report.
Inputs: snapshot aggregate totals only (§0.11 — no raw fact data).
Returns PNG bytes for each chart (embedded in DOCX).
"""

from __future__ import annotations

import io
from decimal import Decimal

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # non-interactive backend; no display required


def _to_float(val) -> float:
    return float(Decimal(str(val))) if val else 0.0


def scope_pie_chart(totals: dict) -> bytes:
    """
    Pie chart: Scope 1 / Scope 2 location-based / Scope 3 breakdown.
    Uses aggregate totals from report_snapshot only.
    """
    labels = ["Scope 1", "Scope 2 (location)", "Scope 3"]
    values = [
        _to_float(totals.get("scope1", 0)),
        _to_float(totals.get("scope2_location", 0)),
        _to_float(totals.get("scope3", 0)),
    ]
    # Filter zero slices
    pairs = [(lbl, v) for lbl, v in zip(labels, values, strict=True) if v > 0]
    if not pairs:
        pairs = [("Aucune donnée", 1)]
    labels_f, values_f = zip(*pairs, strict=False)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(
        values_f,
        labels=labels_f,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#2ecc71", "#3498db", "#e67e22"],
    )
    ax.set_title("Répartition des émissions par scope (tCO₂e)", fontsize=11)
    return _fig_to_png(fig)


def category_bar_chart(computation_trace: list[dict]) -> bytes:
    """
    Horizontal bar chart: emissions per category.
    Aggregates the computation_trace by category (aggregate only — §0.11).
    """
    # Aggregate by category from trace (trace is part of snapshot)
    cat_totals: dict[str, float] = {}
    for line in computation_trace:
        cat = line.get("category", "unknown")
        val = _to_float(line.get("emissions_co2e", 0))
        cat_totals[cat] = cat_totals.get(cat, 0) + val

    if not cat_totals:
        cat_totals = {"Aucune donnée": 0}

    categories = list(cat_totals.keys())
    values = [cat_totals[c] for c in categories]
    # Sort descending
    pairs = sorted(zip(categories, values, strict=True), key=lambda x: x[1], reverse=True)
    cats, vals = zip(*pairs, strict=False) if pairs else (["—"], [0])

    fig, ax = plt.subplots(figsize=(7, max(3, len(cats) * 0.5 + 1)))
    bars = ax.barh(list(cats), list(vals), color="#3498db")
    ax.bar_label(bars, fmt="%.1f", padding=3)
    ax.set_xlabel("tCO₂e")
    ax.set_title("Émissions par catégorie (tCO₂e)", fontsize=11)
    ax.invert_yaxis()
    fig.tight_layout()
    return _fig_to_png(fig)


def scope2_comparison_bar(totals: dict) -> bytes:
    """Bar chart comparing Scope 2 location-based vs market-based (§0 inv 8)."""
    loc = _to_float(totals.get("scope2_location", 0))
    mkt = _to_float(totals.get("scope2_market", 0))

    fig, ax = plt.subplots(figsize=(5, 3))
    bars = ax.bar(
        ["Location-based", "Market-based"],
        [loc, mkt],
        color=["#3498db", "#9b59b6"],
    )
    ax.bar_label(bars, fmt="%.2f tCO₂e", padding=3)
    ax.set_ylabel("tCO₂e")
    ax.set_title("Scope 2 : Location vs Marché (tCO₂e)", fontsize=11)
    fig.tight_layout()
    return _fig_to_png(fig)


def _fig_to_png(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
