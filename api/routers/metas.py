"""Learnable meta topics derived from META_CATEGORIES / feature families."""

from fastapi import APIRouter

from src.metas import META_CATEGORIES

from api.schemas import MetaTopic, MetasListResponse

router = APIRouter(prefix="/v1", tags=["metas"])

_DESCRIPTIONS = {
    "road": "Road surfaces, markings, and pavement cues",
    "infrastructure": "Utility poles, bollards, guardrails, and street furniture",
    "vegetation": "Plant type, density, and climate signals",
    "architecture": "Building style and construction materials",
    "signage": "Signs, scripts, and regulatory markers",
    "vehicle": "Vehicle types, plates, and traffic side cues",
    "coverage": "Camera / Street View coverage patterns",
    "terrain": "Landform and topography clues",
    "language": "Visible language and script evidence",
    "hemisphere": "Broad hemispheric context clues",
}


@router.get("/metas", response_model=MetasListResponse)
def list_metas() -> MetasListResponse:
    topics = [
        MetaTopic(
            id=f"meta:{category}",
            category=category,
            title=category.replace("_", " ").title(),
            description=_DESCRIPTIONS.get(category, f"Learnable meta topic: {category}"),
        )
        for category in META_CATEGORIES
    ]
    return MetasListResponse(topics=topics)
