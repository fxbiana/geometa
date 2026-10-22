"""Practice-round stubs — payloads only; no analysis or scoring yet."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.schemas import (
    AnalysisStatus,
    PracticeAttemptRequest,
    PracticeAttemptResponse,
    PracticeStartResponse,
)
from api.store import practice_store

router = APIRouter(prefix="/v1/practice", tags=["practice"])


@router.post("/start", response_model=PracticeStartResponse)
def start_practice() -> PracticeStartResponse:
    session_id = str(uuid4())
    payload = PracticeStartResponse(
        session_id=session_id,
        prompt_id="stub:road-markings-intro",
        prompt_text=(
            "Look at the lower third of the view. What road-surface or marking "
            "characteristics stand out before guessing a country?"
        ),
        feature_focus="road",
        disclosure_level="hint",
    )
    practice_store.create_session(session_id, payload.model_dump())
    return payload


@router.post("/{session_id}/attempt", response_model=PracticeAttemptResponse)
def record_attempt(
    session_id: str,
    body: PracticeAttemptRequest,
) -> PracticeAttemptResponse:
    if practice_store.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Practice session not found.")
    attempt = PracticeAttemptResponse(
        session_id=session_id,
        attempt_id=str(uuid4()),
        guessed_country=body.guessed_country,
        guessed_region=body.guessed_region,
        recorded=True,
        explanation_summary=(
            "Placeholder explanation: practice feedback is not wired to the "
            "evidence pipeline yet. No geographic claims were invented."
        ),
        status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
    )
    return practice_store.record_attempt(attempt)
