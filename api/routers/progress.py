"""Progress / mastery stub — empty until study evaluation exists."""

from fastapi import APIRouter

from api.schemas import ProgressResponse

router = APIRouter(prefix="/v1", tags=["progress"])


@router.get("/progress", response_model=ProgressResponse)
def get_progress() -> ProgressResponse:
    return ProgressResponse(
        mastery_by_category={},
        rounds_completed=0,
        sample_insufficient=True,
    )
