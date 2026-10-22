"""In-memory stores for the API skeleton (not durable)."""

from __future__ import annotations

from threading import Lock
from typing import Dict, Optional

from api.schemas import AnalysisResultModel, PracticeAttemptResponse


class AnalysisStore:
    def __init__(self) -> None:
        self._items: Dict[str, AnalysisResultModel] = {}
        self._lock = Lock()

    def put(self, result: AnalysisResultModel) -> AnalysisResultModel:
        with self._lock:
            self._items[result.analysis_id] = result
        return result

    def get(self, analysis_id: str) -> Optional[AnalysisResultModel]:
        with self._lock:
            return self._items.get(analysis_id)


class PracticeStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}
        self._attempts: Dict[str, PracticeAttemptResponse] = {}
        self._lock = Lock()

    def create_session(self, session_id: str, payload: dict) -> dict:
        with self._lock:
            self._sessions[session_id] = payload
        return payload

    def get_session(self, session_id: str) -> Optional[dict]:
        with self._lock:
            return self._sessions.get(session_id)

    def record_attempt(self, attempt: PracticeAttemptResponse) -> PracticeAttemptResponse:
        with self._lock:
            self._attempts[attempt.attempt_id] = attempt
        return attempt


analysis_store = AnalysisStore()
practice_store = PracticeStore()
