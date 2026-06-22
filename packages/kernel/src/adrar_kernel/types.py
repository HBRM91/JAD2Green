"""
Frozen dataclasses for all kernel inputs and outputs.
Pure data — no methods, no I/O, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ConversionEdge:
    id: str
    from_unit: str
    to_unit: str
    coefficient: Decimal
    conversion_type: str          # NCV | density | oxidation | direct
    fuel_type: str | None      # None = applies to all fuels
    source: str | None
    effective_from: date
    effective_to: date | None  # None = still valid


@dataclass(frozen=True)
class EmissionFactor:
    id: str
    factor_set_id: str
    category: str
    sub_category: str | None
    gas: str
    value: Decimal                # the factor value (kgCO2e per activity_unit)
    unit: str                     # e.g. kgCO2e/MJ
    activity_unit: str            # e.g. MJ (what the activity must be converted to)
    scope: int
    scope2_type: str | None    # 'location' | 'market' | None
    region: str | None
    source: str | None


@dataclass(frozen=True)
class FactorSet:
    id: str
    methodology_id: str
    version: str
    effective_from: date
    effective_to: date | None
    gwp_basis: str
    region: str | None
    factors: tuple[EmissionFactor, ...]


@dataclass(frozen=True)
class GWPValue:
    gas: str
    gwp_basis: str
    value: Decimal
    time_horizon_years: int


@dataclass(frozen=True)
class ActivityFact:
    id: str
    category: str
    sub_category: str | None
    activity_value: Decimal
    activity_unit: str
    scope: int
    scope2_type: str | None    # 'location' | 'market' | None
    fuel_type: str | None      # conversion graph hint


# ── Computation trace types ────────────────────────────────────────────────

@dataclass(frozen=True)
class ConversionStep:
    edge_id: str
    from_unit: str
    to_unit: str
    coefficient: Decimal
    conversion_type: str
    fuel_type: str | None
    source: str | None


@dataclass(frozen=True)
class ConversionChain:
    steps: tuple[ConversionStep, ...]
    combined_coefficient: Decimal   # product of all step coefficients


@dataclass(frozen=True)
class TraceLineItem:
    """One fact × one emission factor = one line in the computation trace."""
    fact_id: str
    category: str
    sub_category: str | None
    scope: int
    scope2_type: str | None      # which Scope-2 type this line covers
    activity_value: Decimal         # raw input value
    activity_unit: str
    conversion_chain: ConversionChain | None   # None when units already match
    converted_value: Decimal        # in the factor's activity_unit
    factor_id: str
    factor_value: Decimal           # kgCO2e per activity_unit
    gas: str
    gwp_value: Decimal              # GWP of that gas (1 for CO2e factors)
    gwp_basis: str
    emissions_co2e: Decimal         # activity × factor × gwp  (NO uncertainty)


@dataclass(frozen=True)
class UncertaintyRange:
    total_co2e: Decimal    # the point estimate
    fraction: Decimal      # ± fraction (e.g. Decimal('0.05') = ±5%)
    low_co2e: Decimal      # total_co2e × (1 - fraction)
    high_co2e: Decimal     # total_co2e × (1 + fraction)


@dataclass(frozen=True)
class ScopeUncertainty:
    """Uncertainty ranges per scope — stored SEPARATELY from totals (§0 inv 2)."""
    scope1: UncertaintyRange
    scope2_location: UncertaintyRange
    scope2_market: UncertaintyRange
    scope3: UncertaintyRange
    total: UncertaintyRange


@dataclass(frozen=True)
class EmissionResult:
    """Output of compute_emissions. All Decimal; no floats; no uncertainty in totals."""
    # Totals — pure activity × factor × gwp sums (§0 inv 2: no uncertainty term)
    scope1_co2e: Decimal
    scope2_location_co2e: Decimal    # §0 inv 8: dual S2
    scope2_market_co2e: Decimal      # §0 inv 8: dual S2
    scope3_co2e: Decimal
    total_co2e: Decimal              # scope1 + scope2_location + scope3

    # Uncertainty — separate (§0 inv 2)
    uncertainty: ScopeUncertainty

    # Full computation trace (§0 inv 10): every multiplication, factor id, GWP, conversion
    computation_trace: tuple[TraceLineItem, ...]

    # Provenance
    factor_set_versions: tuple[str, ...]   # all factor_set ids used
    gwp_basis: str

    # Deterministic fingerprint of this result (§0 inv 1)
    state_hash: str
