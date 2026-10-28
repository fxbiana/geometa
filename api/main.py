"""GeoMeta FastAPI application entrypoint.

Run from the repository root:

    uvicorn api.main:app --reload

Authentication note
-------------------
# TODO(auth): Clerk JWT verification middleware.
# Frontend will use Next.js + Clerk; verify Bearer JWTs here before protecting
# user-scoped routes. Until then, all routes are unauthenticated local stubs.
# Do not implement Node/Clerk verification in this Python package beyond a
# future shared JWT validation step.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.routers import analyses, health, metas, practice, progress

app = FastAPI(
    title="GeoMeta API",
    description=(
        "HTTP skeleton for the geographic reasoning coach. "
        "Analyses run real source validation and road measurements; "
        "practice/progress endpoints are stubs."
    ),
    version=__version__,
)

# The unpacked Chrome extension calls this API from a chrome-extension origin.
# Local Next.js dev origins stay allowed; other websites do not.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"chrome-extension://[a-p]{32}",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyses.router)
app.include_router(practice.router)
app.include_router(progress.router)
app.include_router(metas.router)
