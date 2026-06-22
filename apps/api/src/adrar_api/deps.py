"""
FastAPI dependencies: JWT auth → tenant context → DB connection with GUC.

Invariant §0.6: every request injects bureau_id + role from auth token into
the DB session via SET LOCAL GUC before any query is executed.
"""

from __future__ import annotations

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
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


def get_tenant(request: Request) -> TenantContext:
    """Validate Bearer JWT and extract tenant context."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth.removeprefix("Bearer ").strip()
    payload = _decode_jwt(token)

    bureau_id = payload.get("bureau_id")
    adrar_role = payload.get("adrar_role")
    user_id = payload.get("sub")

    if not bureau_id:
        raise HTTPException(status_code=401, detail="Token missing bureau_id claim")
    if not adrar_role:
        raise HTTPException(status_code=401, detail="Token missing adrar_role claim")

    return TenantContext(bureau_id=bureau_id, role=adrar_role, user_id=user_id or "")


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
