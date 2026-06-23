from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .limiter import limiter
from .routers import activity, anomalies, compute, documents, factor_sets, intensity, projects, reports, rse

app = FastAPI(
    title="Adrar AI API",
    version="0.1.0",
    description="GHG emissions reporting API for bureaux d'étude.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────
# Restrict to known frontend origins. Override via ALLOWED_ORIGINS env var
# (comma-separated) for production deployment.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)

# ── Global request body size limit (10 MB for JSON endpoints) ─────────────
# File uploads are handled separately with their own 50 MB limit.
_MAX_BODY_BYTES = 10 * 1024 * 1024  # 10 MB


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        if int(content_length) > _MAX_BODY_BYTES:
            # Allow multipart uploads to pass through (they have their own limit)
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" not in content_type:
                return JSONResponse(
                    {"detail": "Request body too large"},
                    status_code=413,
                )
    return await call_next(request)


app.include_router(projects.router, tags=["projects"])
app.include_router(activity.router, tags=["activity"])
app.include_router(factor_sets.router, tags=["factor_sets"])
app.include_router(compute.router, tags=["compute"])
app.include_router(anomalies.router, tags=["anomalies"])
app.include_router(documents.router, tags=["documents"])
app.include_router(reports.router, tags=["reports"])
app.include_router(rse.router, tags=["rse"])
app.include_router(intensity.router, tags=["intensity"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
