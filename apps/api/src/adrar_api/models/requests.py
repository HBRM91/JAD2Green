from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator


class ClientCreate(BaseModel):
    name: str
    sector: str | None = None


class ProjectCreate(BaseModel):
    client_id: str
    name: str
    reporting_year: int
    methodology_id: str


class ProposeActivityRequest(BaseModel):
    """
    Invariant §0.3: nothing automated may write 'validated'.
    The API enforces this; the DB trigger prevents regression.
    """

    category: str
    sub_category: str | None = None
    description: str | None = None
    activity_value: Decimal
    activity_unit: str
    period_start: date
    period_end: date
    scope: Literal[1, 2, 3]
    scope2_type: Literal["location", "market"] | None = None
    fuel_type: str | None = None
    provenance: dict[str, Any] = {}
    # state field: only 'proposed' is accepted from external callers
    state: str = "proposed"

    @field_validator("state")
    @classmethod
    def state_must_be_proposed(cls, v: str) -> str:
        """§0.3: API layer enforces proposed-only writes. Reject any attempt to set validated."""
        if v != "proposed":
            raise ValueError(
                "state must be 'proposed'. Only explicit human action in the UI may "
                "promote a fact to 'validated' (§0 invariant 3)."
            )
        return v

    @model_validator(mode="after")
    def period_order(self) -> ProposeActivityRequest:
        if self.period_end < self.period_start:
            raise ValueError("period_end must be >= period_start")
        return self


class FlagAnomalyRequest(BaseModel):
    activity_fact_id: str | None = None
    anomaly_type: str
    severity: Literal["info", "warning", "error"]
    description: str


class ComputeEmissionsRequest(BaseModel):
    reporting_year: int
    gwp_basis: Literal["AR4", "AR5", "AR6"] = "AR5"
    methodology_id: str
    region: str | None = None
