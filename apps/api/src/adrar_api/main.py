from __future__ import annotations

from fastapi import FastAPI

from .routers import activity, anomalies, compute, factor_sets, projects

app = FastAPI(
    title="Adrar AI API",
    version="0.1.0",
    description="GHG emissions reporting API for bureaux d'étude.",
)

app.include_router(projects.router, tags=["projects"])
app.include_router(activity.router, tags=["activity"])
app.include_router(factor_sets.router, tags=["factor_sets"])
app.include_router(compute.router, tags=["compute"])
app.include_router(anomalies.router, tags=["anomalies"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
