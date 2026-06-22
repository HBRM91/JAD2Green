"""
Factor-set selector and emission-factor matcher.

Invariant §0.7: emission factors are effective-dated.
A FY2024 report uses the factor set valid for FY2024, never "latest".
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .types import ActivityFact, EmissionFactor, FactorSet


class FactorError(Exception):
    pass


def select_factor_set(
    factor_sets: Sequence[FactorSet],
    methodology_id: str,
    region: str | None,
    reporting_year: int,
) -> FactorSet:
    """
    Select the most appropriate factor set for a methodology, region, and year.

    Effective-dating rule: the factor set is valid if
        effective_from <= date(reporting_year, 12, 31) <= effective_to (or effective_to is NULL).

    Region preference: region-specific match beats NULL (global).
    If no region-specific match, falls back to global (NULL).

    Raises FactorError if no match found.
    """
    on_date = date(reporting_year, 12, 31)

    candidates = [
        fs for fs in factor_sets
        if fs.methodology_id == methodology_id
        and fs.effective_from <= on_date
        and (fs.effective_to is None or fs.effective_to >= on_date)
    ]

    # Prefer region-specific
    if region is not None:
        region_match = [fs for fs in candidates if fs.region == region]
        if region_match:
            return _pick_latest(region_match)

    # Fall back to global
    global_match = [fs for fs in candidates if fs.region is None]
    if global_match:
        return _pick_latest(global_match)

    raise FactorError(
        f"No factor set found for methodology={methodology_id!r} "
        f"region={region!r} year={reporting_year}"
    )


def _pick_latest(sets: list[FactorSet]) -> FactorSet:
    """Among multiple matching sets, return the one with the latest effective_from."""
    return max(sets, key=lambda fs: fs.effective_from)


def find_factors_for_fact(
    factors: Sequence[EmissionFactor],
    fact: ActivityFact,
) -> tuple[EmissionFactor, ...]:
    """
    Return the emission factor(s) that match an activity fact.

    For Scope 2: returns BOTH location and market factors (dual-value, §0 inv 8).
    For other scopes: returns the single matching factor.

    Matching rules:
      - scope must match
      - category must match
      - sub_category: if fact has one, factor must match (or factor has None)
      - For Scope 2: ignores fact.scope2_type — returns all scope2_types found
    """
    matches = []
    for f in factors:
        if f.scope != fact.scope:
            continue
        if f.category != fact.category:
            continue
        if fact.sub_category is not None and f.sub_category is not None and f.sub_category != fact.sub_category:
            continue
        matches.append(f)

    if not matches:
        raise FactorError(
            f"No emission factor found for category={fact.category!r} "
            f"sub_category={fact.sub_category!r} scope={fact.scope}"
        )

    return tuple(matches)
