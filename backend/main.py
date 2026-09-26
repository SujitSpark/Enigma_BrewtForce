"""FastAPI application entrypoint.

Run from the project root:

    uvicorn backend.main:app --reload

This app currently exposes ONLY the GIS / Location Intelligence module
(Person 3). Other teammates can mount their own routers alongside it.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.gis_routes import router as gis_router

app = FastAPI(
    title="Industrial Symbiosis Discovery Engine - GIS Module",
    description=(
        "GIS / Location Intelligence backend (Person 3). Provides coordinate "
        "resolution, Haversine distance, radius filtering, nearby discovery, "
        "geographic feasibility scoring, map-ready JSON and pluggable routing. "
        "All bundled industry data is DEMO / PROTOTYPE data."
    ),
    version="0.1.0",
)

# Permissive CORS so the frontend teammate can call this during the hackathon.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gis_router, prefix="/gis")


@app.get("/", tags=["root"])
def root() -> dict:
    return {
        "service": "Industrial Symbiosis Discovery Engine - GIS Module",
        "docs": "/docs",
        "gis_health": "/gis/health",
        "note": "Bundled industry data is DEMO / PROTOTYPE data.",
    }
