from dataclasses import dataclass


@dataclass(frozen=True)
class GeoMetas:
    """Legacy detector clue shape retained at the contract boundary."""

    category: str
    feature: str
    value: str
    confidence: float
    strength: float
    scope: str

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1 or not 0 <= self.strength <= 1:
            raise ValueError("confidence and strength must be between 0 and 1")


META_CATEGORIES = [
    "road",
    "infrastructure",
    "vegetation",
    "architecture",
    "signage",
    "vehicle",
    "coverage",
    "terrain",
    "language",
    "hemisphere",
]

# categorizing fundamentals of meta analysis (key is empty dic for each category)
def create_meta_result(): 
    metas = {}
    for category in META_CATEGORIES:
        metas[category] = {
            "observations" : [],
            "clues": []
        }
    return metas