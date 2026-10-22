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

app.include_router(health.router)
app.include_router(analyses.router)
app.include_router(practice.router)
app.include_router(progress.router)
app.include_router(metas.router)
