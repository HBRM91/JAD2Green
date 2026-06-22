from __future__ import annotations

import uuid as _uuid
from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

import psycopg2
import psycopg2.extras
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt

from .config import settings


@dataclass(frozen=True)
class TenantContext:
    bureau_id: str
    role: str       # admin | consultant | reviewer
    user_id: str


def _decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            # Supabase tokens carry aud="authenticated"; verify it.
            audience="authenticated",
        )
    except JWTError:
        # Generic message — never expose why validation failed (timing/oracle)
        raise HTTPException(status_code=401, detail="Authentication failed")


def _validate_uuid(value: str, field: str) -> str:
    """Reject malformed UUIDs before they reach the DB GUC."""
    try:
        return str(_uuid.UUID(value))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail=f"Invalid {field} in token")


_ALLOWED_ROLES = {"admin", "consultant", "reviewer"}


def get_tenant(request: Request) -> TenantContext:
    """Validate Bearer JWT and extract tenant context."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    payload = _decode_jwt(token)

    bureau_id = payload.get("bureau_id") or ""
    adrar_role = payload.get("adrar_role") or ""
    user_id = payload.get("sub") or ""

    if not bureau_id:
        raise HTTPException(status_code=401, detail="Token missing bureau_id claim")
    if not adrar_role:
        raise HTTPException(status_code=401, detail="Token missing adrar_role claim")

    # Validate UUID shape before injecting into DB GUC (belt-and-suspenders)
    bureau_id = _validate_uuid(bureau_id, "bureau_id")

    # Allowlist role values — never pass arbitrary strings to GUC
    if adrar_role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=401, detail="Invalid role in token")

    return TenantContext(bureau_id=bureau_id, role=adrar_role, user_id=user_id)


TenantDep = Annotated[TenantContext, Depends(get_tenant)]


def get_db(tenant: TenantDep) -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Open a psycopg2 connection and inject tenant GUC before yielding.

    Uses SET LOCAL so GUC is scoped to the transaction (§0 inv 6).
    RLS on every table then enforces isolation (§0 inv 5).
    """
    conn = psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # §0 inv 6: inject tenant context into DB session
            cur.execute("SET LOCAL app.bureau_id = %s", (tenant.bureau_id,))
            cur.execute("SET LOCAL app.role = %s", (tenant.role,))
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


DBDep = Annotated[psycopg2.extensions.connection, Depends(get_db)]
