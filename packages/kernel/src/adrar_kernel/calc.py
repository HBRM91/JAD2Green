"""
Deterministic emissions calculation kernel.

Invariants enforced here:
  §0.1 — pure & deterministic; no LLM, no network, no I/O
  §0.2 — emissions = activity × factor × gwp; NO (1 + uncertainty) term
  §0.8 — dual Scope 2: both location and market computed
  §0.9 — unit conversion is data, not code
  §0.10 — full computation_trace + state_hash
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .conversion import ConversionChain, resolve_conversion
from .factors import find_factors_for_fact
from .types import (
    ActivityFact,
    ConversionEdge,
    EmissionFactor,
    EmissionResult,
    GWPValue,
    ScopeUncertainty,
    TraceLineItem,
    UncertaintyRange,
)

# ── GWP lookup ────────────────────────────────────────────────────────────

class GWPError(Exception):
    pass


def _lookup_gwp(
    gwp_values: Sequence[GWPValue],
    gas: str,
    gwp_basis: str,
    time_horizon_years: int = 100,
) -> Decimal:
    """Return GWP value for a gas. CO2e factors have implicit GWP=1."""
    if gas == "CO2e":
        return Decimal("1")
    for g in gwp_values:
        if g.gas == gas and g.gwp_basis == gwp_basis and g.time_horizon_years == time_horizon_years:
            return g.value
    # CO2 always = 1 regardless of basis
    if gas == "CO2":
        return Decimal("1")
    raise GWPError(f"No GWP found for gas={gas!r} basis={gwp_basis!r} horizon={time_horizon_years}yr")


# ── Unit conversion for a single fact × factor pair ───────────────────────

def _convert_activity(
    fact: ActivityFact,
    factor: EmissionFactor,
    conversion_edges: Sequence[ConversionEdge],
    on_date: date,
) -> tuple[Decimal, ConversionChain | None]:
    """
    Convert fact.activity_value from fact.activity_unit to factor.activity_unit.
    Returns (converted_value, chain_or_None).
    Chain is None when units already match.
    """
    if fact.activity_unit == factor.activity_unit:
        return fact.activity_value, None

    chain = resolve_conversion(
        edges=conversion_edges,
        from_unit=fact.activity_unit,
        to_unit=factor.activity_unit,
        fuel_type=fact.fuel_type,
        on_date=on_date,
    )
    converted = fact.activity_value * chain.combined_coefficient
    return converted, chain


# ── Per-line emission computation ─────────────────────────────────────────

def _compute_line(
    fact: ActivityFact,
    factor: EmissionFactor,
    gwp_values: Sequence[GWPValue],
    conversion_edges: Sequence[ConversionEdge],
    gwp_basis: str,
    on_date: date,
    scope2_type_override: str | None = None,
) -> TraceLineItem:
    """
    Compute one emission line: activity × factor × gwp.
    NO uncertainty term — §0 inv 2.
    """
    converted_value, chain = _convert_activity(fact, factor, conversion_edges, on_date)
    gwp = _lookup_gwp(gwp_values, factor.gas, gwp_basis)
    emissions = converted_value * factor.value * gwp

    scope2_type = scope2_type_override or factor.scope2_type

    return TraceLineItem(
        fact_id=fact.id,
        category=fact.category,
        sub_category=fact.sub_category,
        scope=fact.scope,
        scope2_type=scope2_type,
        activity_value=fact.activity_value,
        activity_unit=fact.activity_unit,
        conversion_chain=chain,
        converted_value=converted_value,
        factor_id=factor.id,
        factor_value=factor.value,
        gas=factor.gas,
        gwp_value=gwp,
        gwp_basis=gwp_basis,
        emissions_co2e=emissions,
    )


# ── Uncertainty (separate from totals — §0 inv 2) ─────────────────────────

# Default IPCC Tier-1 uncertainty fractions by scope.
# These are data-driven defaults; real values would come from the factor DB.
_DEFAULT_UNCERTAINTY: dict[str, Decimal] = {
    "scope1": Decimal("0.05"),          # ±5% stationary combustion
    "scope2_location": Decimal("0.10"), # ±10% grid factor
    "scope2_market": Decimal("0.10"),
    "scope3": Decimal("0.20"),          # ±20% indirect
    "total": Decimal("0.07"),           # combined (conservative)
}


def _make_uncertainty_range(total: Decimal, fraction: Decimal) -> UncertaintyRange:
    low = (total * (Decimal("1") - fraction)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    high = (total * (Decimal("1") + fraction)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return UncertaintyRange(
        total_co2e=total,
        fraction=fraction,
        low_co2e=low,
        high_co2e=high,
    )


def _compute_uncertainty(
    scope1: Decimal,
    scope2_loc: Decimal,
    scope2_mkt: Decimal,
    scope3: Decimal,
    total: Decimal,
) -> ScopeUncertainty:
    """Compute uncertainty ranges — NEVER added to totals (§0 inv 2)."""
    return ScopeUncertainty(
        scope1=_make_uncertainty_range(scope1, _DEFAULT_UNCERTAINTY["scope1"]),
        scope2_location=_make_uncertainty_range(scope2_loc, _DEFAULT_UNCERTAINTY["scope2_location"]),
        scope2_market=_make_uncertainty_range(scope2_mkt, _DEFAULT_UNCERTAINTY["scope2_market"]),
        scope3=_make_uncertainty_range(scope3, _DEFAULT_UNCERTAINTY["scope3"]),
        total=_make_uncertainty_range(total, _DEFAULT_UNCERTAINTY["total"]),
    )


# ── State hash (§0 inv 1 — deterministic fingerprint) ─────────────────────

def _decimal_str(d: Decimal) -> str:
    return format(d, 'f')


def _chain_to_dict(chain: ConversionChain | None) -> dict | None:
    if chain is None:
        return None
    return {
        "combined_coefficient": _decimal_str(chain.combined_coefficient),
        "steps": [
            {
                "edge_id": s.edge_id,
                "from_unit": s.from_unit,
                "to_unit": s.to_unit,
                "coefficient": _decimal_str(s.coefficient),
                "conversion_type": s.conversion_type,
                "fuel_type": s.fuel_type,
            }
            for s in chain.steps
        ],
    }


def _trace_to_dict(line: TraceLineItem) -> dict:
    return {
        "fact_id": line.fact_id,
        "category": line.category,
        "sub_category": line.sub_category,
        "scope": line.scope,
        "scope2_type": line.scope2_type,
        "activity_value": _decimal_str(line.activity_value),
        "activity_unit": line.activity_unit,
        "conversion_chain": _chain_to_dict(line.conversion_chain),
        "converted_value": _decimal_str(line.converted_value),
        "factor_id": line.factor_id,
        "factor_value": _decimal_str(line.factor_value),
        "gas": line.gas,
        "gwp_value": _decimal_str(line.gwp_value),
        "gwp_basis": line.gwp_basis,
        "emissions_co2e": _decimal_str(line.emissions_co2e),
    }


def compute_state_hash(
    scope1_co2e: Decimal,
    scope2_location_co2e: Decimal,
    scope2_market_co2e: Decimal,
    scope3_co2e: Decimal,
    total_co2e: Decimal,
    computation_trace: tuple[TraceLineItem, ...],
    factor_set_versions: tuple[str, ...],
    gwp_basis: str,
) -> str:
    """
    Deterministic SHA-256 of a canonical representation.
    Same inputs → byte-identical hash, forever.
    """
    canonical = {
        "scope1_co2e": _decimal_str(scope1_co2e),
        "scope2_location_co2e": _decimal_str(scope2_location_co2e),
        "scope2_market_co2e": _decimal_str(scope2_market_co2e),
        "scope3_co2e": _decimal_str(scope3_co2e),
        "total_co2e": _decimal_str(total_co2e),
        "gwp_basis": gwp_basis,
        "factor_set_versions": sorted(factor_set_versions),
        # Sort trace by fact_id for canonical ordering
        "computation_trace": sorted(
            [_trace_to_dict(line) for line in computation_trace],
            key=lambda d: (d["fact_id"], d["scope2_type"] or ""),
        ),
    }
    json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


# ── Main entry point ───────────────────────────────────────────────────────

def compute_emissions(
    facts: Sequence[ActivityFact],
    factors: Sequence[EmissionFactor],
    gwp_values: Sequence[GWPValue],
    conversion_edges: Sequence[ConversionEdge],
    gwp_basis: str,
    reporting_year: int,
    factor_set_ids: Sequence[str],
) -> EmissionResult:
    """
    Pure deterministic emissions computation.

    Invariants enforced:
      §0.1 — no I/O, no randomness, no LLM
      §0.2 — totals = activity × factor × gwp only; no uncertainty inflation
      §0.8 — for each Scope 2 fact, both location and market are computed
      §0.9 — conversion is purely from the passed-in edges

    Args:
        facts: validated activity facts (the caller must ensure state='validated')
        factors: emission factors pre-selected for this methodology/region/year
        gwp_values: GWP values for gwp_basis
        conversion_edges: the full conversion graph for the reporting year
        gwp_basis: 'AR5' | 'AR6'
        reporting_year: e.g. 2024
        factor_set_ids: IDs of factor sets used (for provenance)
    """
    on_date = date(reporting_year, 12, 31)
    trace_lines: list[TraceLineItem] = []

    for fact in facts:
        matching_factors = find_factors_for_fact(factors, fact)

        if fact.scope == 2:
            # §0.8: dual Scope 2 — compute both location and market from every match
            for f in matching_factors:
                if f.scope2_type in ("location", "market"):
                    line = _compute_line(
                        fact, f, gwp_values, conversion_edges, gwp_basis, on_date
                    )
                    trace_lines.append(line)
        else:
            # Scope 1 or 3: use all matching factors (typically one)
            for f in matching_factors:
                line = _compute_line(
                    fact, f, gwp_values, conversion_edges, gwp_basis, on_date
                )
                trace_lines.append(line)

    # Sum up by scope
    scope1 = sum(
        (ln.emissions_co2e for ln in trace_lines if ln.scope == 1),
        Decimal("0"),
    )
    scope2_loc = sum(
        (ln.emissions_co2e for ln in trace_lines if ln.scope == 2 and ln.scope2_type == "location"),
        Decimal("0"),
    )
    scope2_mkt = sum(
        (ln.emissions_co2e for ln in trace_lines if ln.scope == 2 and ln.scope2_type == "market"),
        Decimal("0"),
    )
    scope3 = sum(
        (ln.emissions_co2e for ln in trace_lines if ln.scope == 3),
        Decimal("0"),
    )
    # total uses location-based for Scope 2 (GHG Protocol primary method)
    total = scope1 + scope2_loc + scope3

    uncertainty = _compute_uncertainty(scope1, scope2_loc, scope2_mkt, scope3, total)

    trace_tuple = tuple(trace_lines)
    versions_tuple = tuple(sorted(set(factor_set_ids)))

    state_hash = compute_state_hash(
        scope1, scope2_loc, scope2_mkt, scope3, total,
        trace_tuple, versions_tuple, gwp_basis,
    )

    return EmissionResult(
        scope1_co2e=scope1,
        scope2_location_co2e=scope2_loc,
        scope2_market_co2e=scope2_mkt,
        scope3_co2e=scope3,
        total_co2e=total,
        uncertainty=uncertainty,
        computation_trace=trace_tuple,
        factor_set_versions=versions_tuple,
        gwp_basis=gwp_basis,
        state_hash=state_hash,
    )
