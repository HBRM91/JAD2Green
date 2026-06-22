"""
Phase 2 acceptance tests for the pure kernel.

Acceptance criteria:
  1. Determinism: same inputs → identical totals AND identical state_hash
  2. Dual Scope 2 present: both location and market totals
  3. Uncertainty NOT in totals: totals are activity × factor × gwp only
  4. Conversion-as-data: editing a coefficient changes result with zero code change
  5. Effective-dating: FY2023 vs FY2024 select different factor sets
  6. No uncertainty term in total_co2e (§0 inv 2)
  7. Multi-hop conversion works correctly
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from adrar_kernel import (
    ActivityFact,
    ConversionEdge,
    ConversionError,
    EmissionFactor,
    EmissionResult,
    FactorSet,
    GWPValue,
    compute_emissions,
    resolve_conversion,
    select_factor_set,
)

# ── Shared test fixtures ───────────────────────────────────────────────────

def _edge(id_, from_, to_, coeff, ctype, fuel=None, eff_from=date(2020, 1, 1)):
    return ConversionEdge(
        id=id_,
        from_unit=from_,
        to_unit=to_,
        coefficient=Decimal(str(coeff)),
        conversion_type=ctype,
        fuel_type=fuel,
        source="test",
        effective_from=eff_from,
        effective_to=None,
    )


def _factor(id_, fs_id, category, gas, value, activity_unit, scope, scope2_type=None, sub_cat=None):
    return EmissionFactor(
        id=id_,
        factor_set_id=fs_id,
        category=category,
        sub_category=sub_cat,
        gas=gas,
        value=Decimal(str(value)),
        unit=f"kgCO2e/{activity_unit}",
        activity_unit=activity_unit,
        scope=scope,
        scope2_type=scope2_type,
        region=None,
        source="test",
    )


def _fact(id_, category, value, unit, scope, scope2_type=None, fuel=None, sub_cat=None):
    return ActivityFact(
        id=id_,
        category=category,
        sub_category=sub_cat,
        activity_value=Decimal(str(value)),
        activity_unit=unit,
        scope=scope,
        scope2_type=scope2_type,
        fuel_type=fuel,
    )


def _gwp(gas, basis, value):
    return GWPValue(gas=gas, gwp_basis=basis, value=Decimal(str(value)), time_horizon_years=100)


def _factor_set(id_, methodology_id, version, eff_from, eff_to, gwp_basis, factors, region=None):
    return FactorSet(
        id=id_,
        methodology_id=methodology_id,
        version=version,
        effective_from=eff_from,
        effective_to=eff_to,
        gwp_basis=gwp_basis,
        region=region,
        factors=tuple(factors),
    )


# ── Canonical test scenario ────────────────────────────────────────────────

EDGES = (
    _edge("e1", "L", "MJ", "34.93", "NCV", fuel="diesel"),
    _edge("e2", "MJ", "kWh", "0.2778", "direct"),
    _edge("e3", "kWh", "MJ", "3.6", "direct"),
    _edge("e4", "t", "kg", "1000", "direct"),
    _edge("e5", "kg", "t", "0.001", "direct"),
    _edge("e6", "L", "MJ", "31.82", "NCV", fuel="gasoline"),
)

GWP_VALUES = (
    _gwp("CO2", "AR5", 1),
    _gwp("CH4", "AR5", 28),
    _gwp("N2O", "AR5", 265),
    _gwp("CO2e", "AR5", 1),
)

FACTORS = (
    # Scope 1 — diesel combustion (kgCO2e per MJ)
    _factor("f1", "fs2024", "scope1_mobile", "CO2e", "0.07443", "MJ", 1),
    # Scope 2 — electricity location-based (kgCO2e per kWh)
    _factor("f2", "fs2024", "scope2_electricity", "CO2e", "0.679", "kWh", 2, scope2_type="location"),
    # Scope 2 — electricity market-based (kgCO2e per kWh)
    _factor("f3", "fs2024", "scope2_electricity", "CO2e", "0.679", "kWh", 2, scope2_type="market"),
)

FACTS = (
    # 100 L diesel (scope 1) — must convert L→MJ before applying factor
    _fact("fact1", "scope1_mobile", 100, "L", 1, fuel="diesel"),
    # 500 kWh electricity (scope 2)
    _fact("fact2", "scope2_electricity", 500, "kWh", 2),
)


def _run(**kwargs) -> EmissionResult:
    return compute_emissions(
        facts=kwargs.get("facts", FACTS),
        factors=kwargs.get("factors", FACTORS),
        gwp_values=kwargs.get("gwp_values", GWP_VALUES),
        conversion_edges=kwargs.get("edges", EDGES),
        gwp_basis=kwargs.get("gwp_basis", "AR5"),
        reporting_year=kwargs.get("reporting_year", 2024),
        factor_set_ids=["fs2024"],
    )


# ── 1. Determinism ────────────────────────────────────────────────────────

def test_same_inputs_same_totals():
    r1 = _run()
    r2 = _run()
    assert r1.scope1_co2e == r2.scope1_co2e
    assert r1.scope2_location_co2e == r2.scope2_location_co2e
    assert r1.scope2_market_co2e == r2.scope2_market_co2e
    assert r1.total_co2e == r2.total_co2e


def test_same_inputs_same_state_hash():
    r1 = _run()
    r2 = _run()
    assert r1.state_hash == r2.state_hash
    assert isinstance(r1.state_hash, str)
    assert len(r1.state_hash) == 64  # SHA-256 hex


def test_different_facts_different_hash():
    facts_a = (FACTS[0],)   # diesel only
    facts_b = (FACTS[1],)   # electricity only
    r1 = _run(facts=facts_a)
    r2 = _run(facts=facts_b)
    assert r1.state_hash != r2.state_hash


# ── 2. Dual Scope 2 ───────────────────────────────────────────────────────

def test_scope2_both_location_and_market_present():
    r = _run()
    assert r.scope2_location_co2e > Decimal("0"), "location-based S2 must be > 0"
    assert r.scope2_market_co2e > Decimal("0"), "market-based S2 must be > 0"


def test_scope2_values_are_independent():
    """Location and market can differ; both must always be present."""
    loc_factor = _factor("f2b", "fs2024", "scope2_electricity", "CO2e", "0.500", "kWh", 2, scope2_type="location")
    mkt_factor = _factor("f3b", "fs2024", "scope2_electricity", "CO2e", "0.250", "kWh", 2, scope2_type="market")
    r = _run(factors=(FACTORS[0], loc_factor, mkt_factor))
    assert r.scope2_location_co2e != r.scope2_market_co2e
    # Both are still non-zero
    assert r.scope2_location_co2e > Decimal("0")
    assert r.scope2_market_co2e > Decimal("0")


# ── 3. Uncertainty NOT in totals (§0 inv 2) ───────────────────────────────

def test_totals_have_no_uncertainty_inflation():
    """
    total_co2e must equal scope1 + scope2_location + scope3 exactly.
    No (1 + uncertainty) factor anywhere.
    """
    r = _run()
    expected_total = r.scope1_co2e + r.scope2_location_co2e + r.scope3_co2e
    assert r.total_co2e == expected_total, (
        f"total_co2e={r.total_co2e} != scope1+scope2_loc+scope3={expected_total}. "
        "Uncertainty must NOT be in totals."
    )


def test_uncertainty_separate_from_totals():
    """Uncertainty ranges exist but are in a separate field."""
    r = _run()
    u = r.uncertainty
    # Uncertainty fields exist and are positive
    assert u.scope1.fraction > Decimal("0")
    assert u.scope2_location.fraction > Decimal("0")
    # Uncertainty total does NOT equal total_co2e (it has a range)
    assert u.total.low_co2e < r.total_co2e
    assert u.total.high_co2e > r.total_co2e


def test_uncertainty_point_estimate_matches_total():
    """The uncertainty's total_co2e field must match the actual total."""
    r = _run()
    assert r.uncertainty.total.total_co2e == r.total_co2e


# ── 4. Conversion-as-data ─────────────────────────────────────────────────

def test_changing_coefficient_changes_result():
    """
    Editing a conversion coefficient must change the result with zero code change.
    §0 inv 9: conversion is data, not code.
    """
    # Standard: L diesel → MJ at 34.93 MJ/L
    r_standard = _run()

    # Modified: change diesel NCV coefficient from 34.93 to 40.00
    modified_edges = tuple(
        _edge(e.id, e.from_unit, e.to_unit, "40.00", e.conversion_type, fuel=e.fuel_type)
        if e.id == "e1" else e
        for e in EDGES
    )
    r_modified = _run(edges=modified_edges)

    assert r_standard.scope1_co2e != r_modified.scope1_co2e, (
        "Changing a conversion coefficient must change results."
    )
    # The ratio should match the coefficient ratio
    expected_ratio = Decimal("40.00") / Decimal("34.93")
    actual_ratio = r_modified.scope1_co2e / r_standard.scope1_co2e
    assert abs(actual_ratio - expected_ratio) < Decimal("0.0001"), (
        f"Expected ratio {expected_ratio}, got {actual_ratio}"
    )


def test_changing_coefficient_changes_state_hash():
    """Coefficient change must also change the state_hash."""
    r1 = _run()
    modified_edges = tuple(
        _edge(e.id, e.from_unit, e.to_unit, "40.00", e.conversion_type, fuel=e.fuel_type)
        if e.id == "e1" else e
        for e in EDGES
    )
    r2 = _run(edges=modified_edges)
    assert r1.state_hash != r2.state_hash


# ── 5. Effective-dating ───────────────────────────────────────────────────

def test_effective_dating_different_years_different_sets():
    """
    FY2023 and FY2024 factor sets must be selected by effective date.
    A fact for FY2023 uses the FY2023 set; FY2024 uses FY2024.
    """
    fs_2023 = _factor_set(
        "fs-2023", "m1", "21.0",
        eff_from=date(2023, 1, 1), eff_to=date(2023, 12, 31),
        gwp_basis="AR5", factors=[],
    )
    fs_2024 = _factor_set(
        "fs-2024", "m1", "22.0",
        eff_from=date(2024, 1, 1), eff_to=None,
        gwp_basis="AR5", factors=[],
    )

    selected_2023 = select_factor_set([fs_2023, fs_2024], "m1", None, 2023)
    selected_2024 = select_factor_set([fs_2023, fs_2024], "m1", None, 2024)

    assert selected_2023.id == "fs-2023", f"Expected fs-2023, got {selected_2023.id}"
    assert selected_2024.id == "fs-2024", f"Expected fs-2024, got {selected_2024.id}"


def test_effective_dating_year_boundary():
    """
    A factor set that ended 2023-12-31 must NOT be selected for FY2024.
    """
    fs_old = _factor_set(
        "fs-old", "m1", "20.0",
        eff_from=date(2022, 1, 1), eff_to=date(2022, 12, 31),
        gwp_basis="AR5", factors=[],
    )
    fs_new = _factor_set(
        "fs-new", "m1", "22.0",
        eff_from=date(2023, 1, 1), eff_to=None,
        gwp_basis="AR5", factors=[],
    )

    # FY2024 must use fs-new (fs-old ended in 2022)
    result = select_factor_set([fs_old, fs_new], "m1", None, 2024)
    assert result.id == "fs-new"


def test_effective_dating_region_specificity():
    """Region-specific factor set beats global for matching region."""
    fs_global = _factor_set(
        "fs-global", "m1", "22.0",
        eff_from=date(2024, 1, 1), eff_to=None,
        gwp_basis="AR5", factors=[], region=None,
    )
    fs_ma = _factor_set(
        "fs-ma", "m1", "22.0-MA",
        eff_from=date(2024, 1, 1), eff_to=None,
        gwp_basis="AR5", factors=[], region="MA",
    )

    result_ma = select_factor_set([fs_global, fs_ma], "m1", "MA", 2024)
    result_eu = select_factor_set([fs_global, fs_ma], "m1", "EU", 2024)

    assert result_ma.id == "fs-ma"
    assert result_eu.id == "fs-global"  # no EU-specific, falls back to global


# ── 6. Computation trace completeness ─────────────────────────────────────

def test_trace_contains_every_fact():
    r = _run()
    traced_fact_ids = {line.fact_id for line in r.computation_trace}
    for fact in FACTS:
        assert fact.id in traced_fact_ids, f"Fact {fact.id} missing from trace"


def test_trace_scope2_has_both_types():
    """For the Scope 2 electricity fact, trace must have both location and market lines."""
    r = _run()
    scope2_lines = [ln for ln in r.computation_trace if ln.scope == 2]
    types_present = {ln.scope2_type for ln in scope2_lines}
    assert "location" in types_present, "Trace missing location-based S2 line"
    assert "market" in types_present, "Trace missing market-based S2 line"


def test_trace_emissions_sum_matches_totals():
    """Sum of trace lines must equal the scope totals."""
    r = _run()
    trace_s1 = sum(ln.emissions_co2e for ln in r.computation_trace if ln.scope == 1)
    trace_s2_loc = sum(
        ln.emissions_co2e for ln in r.computation_trace
        if ln.scope == 2 and ln.scope2_type == "location"
    )
    assert trace_s1 == r.scope1_co2e
    assert trace_s2_loc == r.scope2_location_co2e


# ── 7. Conversion graph ────────────────────────────────────────────────────

def test_single_hop_conversion():
    """L → MJ for diesel: one NCV edge."""
    chain = resolve_conversion(EDGES, "L", "MJ", "diesel", date(2024, 12, 31))
    assert len(chain.steps) == 1
    assert chain.combined_coefficient == Decimal("34.93")


def test_multi_hop_conversion():
    """L → kWh for diesel: L→MJ (NCV) → kWh (direct) — two hops."""
    chain = resolve_conversion(EDGES, "L", "kWh", "diesel", date(2024, 12, 31))
    assert len(chain.steps) == 2
    expected = Decimal("34.93") * Decimal("0.2778")
    assert abs(chain.combined_coefficient - expected) < Decimal("0.0001")


def test_fuel_specific_beats_generic():
    """When both fuel-specific and generic edges exist, fuel-specific wins."""
    edges_with_generic = EDGES + (
        _edge("e_gen", "L", "MJ", "99.99", "NCV", fuel=None),
    )
    chain = resolve_conversion(edges_with_generic, "L", "MJ", "diesel", date(2024, 12, 31))
    # Should use the diesel-specific edge (34.93), not the generic (99.99)
    assert chain.combined_coefficient == Decimal("34.93")


def test_identity_conversion():
    """Same from and to unit returns identity chain (coefficient = 1)."""
    chain = resolve_conversion(EDGES, "kWh", "kWh", None, date(2024, 12, 31))
    assert chain.combined_coefficient == Decimal("1")
    assert len(chain.steps) == 0


def test_no_path_raises_conversion_error():
    """Unreachable target raises ConversionError."""
    with pytest.raises(ConversionError):
        resolve_conversion(EDGES, "L", "parsecs", "diesel", date(2024, 12, 31))


def test_effective_dating_excludes_future_edges():
    """An edge not yet effective must not be used."""
    future_edge = _edge("future", "L", "parsecs", "999", "NCV", eff_from=date(2099, 1, 1))
    with pytest.raises(ConversionError):
        resolve_conversion(
            EDGES + (future_edge,), "L", "parsecs", "diesel", date(2024, 12, 31)
        )


# ── 8. Known-value regression ─────────────────────────────────────────────

def test_scope1_diesel_known_value():
    """
    100 L diesel × 34.93 MJ/L × 0.07443 kgCO2e/MJ × 1 (CO2e GWP) = 259.87 kgCO2e
    """
    r = _run(facts=(FACTS[0],))
    expected = Decimal("100") * Decimal("34.93") * Decimal("0.07443")
    assert abs(r.scope1_co2e - expected) < Decimal("0.001"), (
        f"Expected ~{expected}, got {r.scope1_co2e}"
    )


def test_scope2_electricity_known_value():
    """500 kWh × 0.679 kgCO2e/kWh = 339.5 kgCO2e for both location and market."""
    r = _run(facts=(FACTS[1],))
    expected = Decimal("500") * Decimal("0.679")
    assert abs(r.scope2_location_co2e - expected) < Decimal("0.001")
    assert abs(r.scope2_market_co2e - expected) < Decimal("0.001")
