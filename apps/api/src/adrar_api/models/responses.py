from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class ClientResponse(BaseModel):
    id: str
    bureau_id: str
    name: str
    sector: str | None
    naics_code: str | None = None
    secteur_maroc: str | None = None
    is_listed_bvc: bool = False
    rse_reporting_required: bool = False
    created_at: datetime


class ProjectResponse(BaseModel):
    id: str
    bureau_id: str
    client_id: str
    name: str
    reporting_year: int
    methodology_id: str
    status: str
    reporting_frameworks: list[str] | None = None
    sector_code: str | None = None
    language: str | None = None
    ndc_target_year: int | None = None
    ndc_baseline_year: int | None = None
    created_at: datetime


class ActivityFactResponse(BaseModel):
    id: str
    bureau_id: str
    project_id: str
    category: str
    sub_category: str | None
    description: str | None
    activity_value: Decimal
    activity_unit: str
    period_start: date
    period_end: date
    scope: int
    scope2_type: str | None
    state: str
    provenance: dict[str, Any]
    created_at: datetime


class AnomalyResponse(BaseModel):
    id: str
    bureau_id: str
    project_id: str
    activity_fact_id: str | None
    anomaly_type: str
    severity: str
    description: str
    resolved: bool
    created_at: datetime


class FactorSetSummary(BaseModel):
    id: str
    methodology_id: str
    name: str
    version: str
    effective_from: date
    effective_to: date | None
    gwp_basis: str
    region: str | None


class ConversionResponse(BaseModel):
    from_unit: str
    to_unit: str
    fuel_type: str | None
    combined_coefficient: Decimal
    steps: list[dict[str, Any]]


class UncertaintyRangeResponse(BaseModel):
    total_co2e: Decimal
    fraction: Decimal
    low_co2e: Decimal
    high_co2e: Decimal


class ScopeUncertaintyResponse(BaseModel):
    scope1: UncertaintyRangeResponse
    scope2_location: UncertaintyRangeResponse
    scope2_market: UncertaintyRangeResponse
    scope3: UncertaintyRangeResponse
    total: UncertaintyRangeResponse


class ReportSnapshotResponse(BaseModel):
    id: str
    bureau_id: str
    project_id: str
    reporting_year: int
    state_hash: str
    totals_co2e: dict[str, Any]
    scope2_location_t: Decimal | None
    scope2_market_t: Decimal | None
    gwp_basis: str
    uncertainty: dict[str, Any]
    computation_trace: list[dict[str, Any]]
    factor_set_versions: list[str]
    reconciliation: dict[str, Any]
    gri_305_data: dict[str, Any] | None = None
    ndc_alignment: dict[str, Any] | None = None
    intensity_metrics: dict[str, Any] | None = None
    created_at: datetime
