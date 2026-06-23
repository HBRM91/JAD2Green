"""
Orchestration layer: fetch DB data → call pure kernel → persist snapshot.

Invariants:
  §0.1 — kernel call is pure; no I/O inside it
  §0.2 — totals contain no uncertainty
  §0.10 — snapshot is immutable once written
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import psycopg2.extensions
from adrar_kernel import (
    ActivityFact,
    ConversionEdge,
    EmissionFactor,
    GWPValue,
    compute_emissions,
)
from adrar_kernel.factors import FactorError


class ComputeError(Exception):
    pass


def _fetch_validated_facts(
    cur: psycopg2.extensions.cursor,
    project_id: str,
) -> list[ActivityFact]:
    cur.execute(
        """
        SELECT id, category, sub_category, activity_value, activity_unit,
               scope, scope2_type, provenance
        FROM activity_facts
        WHERE project_id = %s AND state = 'validated'
        """,
        (project_id,),
    )
    facts = []
    for r in cur.fetchall():
        fuel_type = r["provenance"].get("fuel_type") if r["provenance"] else None
        facts.append(
            ActivityFact(
                id=str(r["id"]),
                category=r["category"],
                sub_category=r["sub_category"],
                activity_value=Decimal(str(r["activity_value"])),
                activity_unit=r["activity_unit"],
                scope=r["scope"],
                scope2_type=r["scope2_type"],
                fuel_type=fuel_type,
            )
        )
    return facts


def _check_no_proposed_facts(cur: psycopg2.extensions.cursor, project_id: str) -> None:
    """Block compute if any un-validated (proposed) facts remain."""
    cur.execute(
        "SELECT COUNT(*) AS n FROM activity_facts WHERE project_id = %s AND state = 'proposed'",
        (project_id,),
    )
    row = cur.fetchone()
    if row and row["n"] > 0:
        raise ComputeError(
            f"Cannot compute: {row['n']} activity fact(s) are still in 'proposed' state. "
            "All facts must be validated by a consultant before computing emissions."
        )


def _fetch_emission_factors(
    cur: psycopg2.extensions.cursor,
    methodology_id: str,
    region: str | None,
    reporting_year: int,
) -> tuple[list[EmissionFactor], list[str]]:
    on_date = date(reporting_year, 12, 31)
    cur.execute(
        """
        SELECT ef.id, ef.factor_set_id, ef.category, ef.sub_category, ef.gas,
               ef.value, ef.unit, ef.activity_unit, ef.scope, ef.scope2_type,
               ef.region, ef.source
        FROM emission_factors ef
        JOIN factor_sets fs ON fs.id = ef.factor_set_id
        WHERE fs.methodology_id = %s
          AND fs.effective_from <= %s
          AND (fs.effective_to IS NULL OR fs.effective_to >= %s)
          AND (fs.region = %s OR fs.region IS NULL)
        ORDER BY fs.region NULLS LAST, fs.effective_from DESC
        """,
        (methodology_id, on_date, on_date, region),
    )
    factors = []
    factor_set_ids: set[str] = set()
    for r in cur.fetchall():
        factors.append(
            EmissionFactor(
                id=str(r["id"]),
                factor_set_id=str(r["factor_set_id"]),
                category=r["category"],
                sub_category=r["sub_category"],
                gas=r["gas"],
                value=Decimal(str(r["value"])),
                unit=r["unit"],
                activity_unit=r["activity_unit"],
                scope=r["scope"],
                scope2_type=r["scope2_type"],
                region=r["region"],
                source=r["source"],
            )
        )
        factor_set_ids.add(str(r["factor_set_id"]))
    return factors, sorted(factor_set_ids)


def _fetch_conversion_edges(
    cur: psycopg2.extensions.cursor,
    reporting_year: int,
) -> list[ConversionEdge]:
    on_date = date(reporting_year, 12, 31)
    cur.execute(
        """
        SELECT id, from_unit, to_unit, coefficient, conversion_type, fuel_type,
               source, effective_from, effective_to
        FROM conversion_factors
        WHERE effective_from <= %s AND (effective_to IS NULL OR effective_to >= %s)
        """,
        (on_date, on_date),
    )
    return [
        ConversionEdge(
            id=str(r["id"]),
            from_unit=r["from_unit"],
            to_unit=r["to_unit"],
            coefficient=Decimal(str(r["coefficient"])),
            conversion_type=r["conversion_type"],
            fuel_type=r["fuel_type"],
            source=r["source"],
            effective_from=r["effective_from"],
            effective_to=r["effective_to"],
        )
        for r in cur.fetchall()
    ]


def _fetch_gwp_values(
    cur: psycopg2.extensions.cursor,
    gwp_basis: str,
) -> list[GWPValue]:
    cur.execute(
        "SELECT gas, gwp_basis, value, time_horizon_years FROM gwp_values WHERE gwp_basis = %s",
        (gwp_basis,),
    )
    return [
        GWPValue(
            gas=r["gas"],
            gwp_basis=r["gwp_basis"],
            value=Decimal(str(r["value"])),
            time_horizon_years=r["time_horizon_years"],
        )
        for r in cur.fetchall()
    ]


def _uncertainty_to_dict(u: object) -> dict:
    def _range(r: object) -> dict:
        return {
            "total_co2e": str(r.total_co2e),
            "fraction": str(r.fraction),
            "low_co2e": str(r.low_co2e),
            "high_co2e": str(r.high_co2e),
        }

    return {
        "scope1": _range(u.scope1),
        "scope2_location": _range(u.scope2_location),
        "scope2_market": _range(u.scope2_market),
        "scope3": _range(u.scope3),
        "total": _range(u.total),
    }


def _compute_gri_305(result: object) -> dict | None:
    """
    Derive GRI 305-1/2-loc/2-mkt/3/4 from kernel result.
    Returns None if all zeros (no data).
    """
    s1 = float(result.scope1_co2e)
    s2l = float(result.scope2_location_co2e)
    s2m = float(result.scope2_market_co2e)
    s3 = float(result.scope3_co2e)
    total = s1 + s2l + s3
    if total == 0:
        return None
    return {
        "305-1": round(s1, 4),
        "305-2-loc": round(s2l, 4),
        "305-2-mkt": round(s2m, 4),
        "305-3": round(s3, 4),
        "305-total-loc": round(s1 + s2l + s3, 4),
        "305-total-mkt": round(s1 + s2m + s3, 4),
    }


def _compute_ndc_alignment(
    cur: psycopg2.extensions.cursor,
    project_id: str,
    result: object,
    reporting_year: int,
) -> dict | None:
    """
    Compute NDC Morocco alignment for region=MA projects.
    Morocco NDC target: -45.5% vs BAU by 2030 from 2010 baseline.
    Only meaningful if we have a baseline in the project.
    """
    cur.execute(
        "SELECT ndc_target_year, ndc_baseline_year FROM projects WHERE id = %s",
        (project_id,),
    )
    row = cur.fetchone()
    if not row or not row.get("ndc_baseline_year"):
        return None

    baseline_year = row["ndc_baseline_year"]
    target_year = row.get("ndc_target_year") or 2030

    # Look for a snapshot from the baseline year to compare
    cur.execute(
        """
        SELECT totals_co2e FROM report_snapshots
        WHERE project_id = %s AND reporting_year = %s
        ORDER BY created_at DESC LIMIT 1
        """,
        (project_id, baseline_year),
    )
    baseline_row = cur.fetchone()
    if not baseline_row:
        return None

    baseline_totals = baseline_row["totals_co2e"]
    baseline_total = float(baseline_totals.get("total", 0))
    current_total = float(result.total_co2e)

    if baseline_total == 0:
        return None

    ndc_target_pct = 0.455  # Morocco NDC: -45.5% vs BAU
    target_emissions = baseline_total * (1 - ndc_target_pct)
    reduction_achieved = baseline_total - current_total
    progress_pct = (reduction_achieved / (baseline_total * ndc_target_pct)) * 100 if baseline_total > 0 else 0

    return {
        "baseline_year": baseline_year,
        "target_year": target_year,
        "target_reduction_pct": 45.5,
        "baseline_emissions": round(baseline_total, 4),
        "current_emissions": round(current_total, 4),
        "target_emissions": round(target_emissions, 4),
        "reduction_achieved": round(reduction_achieved, 4),
        "progress_pct": round(progress_pct, 2),
        "on_track": progress_pct >= ((reporting_year - baseline_year) / (target_year - baseline_year)) * 100 if target_year > baseline_year else None,
    }


def run_compute_and_persist(
    conn: psycopg2.extensions.connection,
    project_id: str,
    bureau_id: str,
    user_id: str,
    methodology_id: str,
    region: str | None,
    reporting_year: int,
    gwp_basis: str,
) -> dict:
    """
    Full compute pipeline:
      1. Block if proposed facts exist
      2. Fetch validated facts
      3. Fetch factors, edges, GWP
      4. Call pure kernel
      5. Persist immutable snapshot (§0 inv 10)
      6. Return snapshot dict
    """
    with conn.cursor() as cur:
        _check_no_proposed_facts(cur, project_id)

        facts = _fetch_validated_facts(cur, project_id)
        if not facts:
            raise ComputeError("No validated activity facts found for this project.")

        factors, factor_set_ids = _fetch_emission_factors(
            cur, methodology_id, region, reporting_year
        )
        if not factors:
            raise FactorError(
                f"No emission factors found for methodology={methodology_id!r} "
                f"region={region!r} year={reporting_year}"
            )

        edges = _fetch_conversion_edges(cur, reporting_year)
        gwp_values = _fetch_gwp_values(cur, gwp_basis)

        # Call the pure kernel (§0 inv 1: no I/O inside)
        result = compute_emissions(
            facts=facts,
            factors=factors,
            gwp_values=gwp_values,
            conversion_edges=edges,
            gwp_basis=gwp_basis,
            reporting_year=reporting_year,
            factor_set_ids=factor_set_ids,
        )

        # Build JSONB columns
        totals = {
            "scope1": str(result.scope1_co2e),
            "scope2_location": str(result.scope2_location_co2e),
            "scope2_market": str(result.scope2_market_co2e),
            "scope3": str(result.scope3_co2e),
            "total": str(result.total_co2e),
        }
        trace_json = [
            {
                "fact_id": ln.fact_id,
                "category": ln.category,
                "scope": ln.scope,
                "scope2_type": ln.scope2_type,
                "activity_value": str(ln.activity_value),
                "activity_unit": ln.activity_unit,
                "converted_value": str(ln.converted_value),
                "factor_id": ln.factor_id,
                "factor_value": str(ln.factor_value),
                "gas": ln.gas,
                "gwp_value": str(ln.gwp_value),
                "emissions_co2e": str(ln.emissions_co2e),
            }
            for ln in result.computation_trace
        ]

        # GRI 305 auto-derivation (Morocco reporting enhancement)
        gri_305 = _compute_gri_305(result)
        ndc = _compute_ndc_alignment(cur, project_id, result, reporting_year)

        cur.execute(
            """
            INSERT INTO report_snapshots
                (bureau_id, project_id, reporting_year, state_hash,
                 totals_co2e, scope2_location_t, scope2_market_t,
                 computation_trace, factor_set_versions, gwp_basis,
                 uncertainty, reconciliation, gri_305_data, ndc_alignment, generated_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'{}', %s, %s, %s)
            RETURNING id, bureau_id, project_id, reporting_year, state_hash,
                      totals_co2e, scope2_location_t, scope2_market_t,
                      computation_trace, factor_set_versions, gwp_basis,
                      uncertainty, reconciliation, gri_305_data, ndc_alignment,
                      intensity_metrics, created_at
            """,
            (
                bureau_id,
                project_id,
                reporting_year,
                result.state_hash,
                json.dumps(totals),
                str(result.scope2_location_co2e),
                str(result.scope2_market_co2e),
                json.dumps(trace_json),
                json.dumps(list(result.factor_set_versions)),
                gwp_basis,
                json.dumps(_uncertainty_to_dict(result.uncertainty)),
                json.dumps(gri_305) if gri_305 else None,
                json.dumps(ndc) if ndc else None,
                user_id,
            ),
        )
        row = cur.fetchone()

    return dict(row)
