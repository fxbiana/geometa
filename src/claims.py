"""Versioned geographic claims for road observations.

Only approved, production-ready claim versions may emit Evidence.  Country
associations in this catalog are intentionally SMALL and marked provisional /
low-confidence — they exist to exercise the observation → evidence bridge, not
to assert calibrated geography.
"""

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple


CLAIM_CATALOG_VERSION = "road-claims-v1"


@dataclass(frozen=True)
class ClaimVersion:
    """Immutable mapping from an observation pattern to geographic scope."""

    id: str
    observation_pattern: str
    geographic_scope: str
    diagnosticity: float
    reliability: float
    supports: Tuple[str, ...] = field(default_factory=tuple)
    weakens: Tuple[str, ...] = field(default_factory=tuple)
    feature_key: Optional[str] = None
    production_ready: bool = False
    review_status: str = "proposed"
    claim_truth_confidence: float = 0.0
    notes: str = ""

    def __post_init__(self) -> None:
        for name in ("diagnosticity", "reliability", "claim_truth_confidence"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


# Curated in-repo catalog for existing road observations only.
# Country sets are provisional teaching stubs — not empirically validated.
ROAD_CLAIMS_V1: Tuple[ClaimVersion, ...] = (
    ClaimVersion(
        id="claim:road:yellow_center_line:v1",
        observation_pattern="possible_yellow_marking",
        geographic_scope="country",
        diagnosticity=0.35,
        reliability=0.40,
        supports=("US", "CA"),
        weakens=(),
        feature_key="yellow_percentage",
        production_ready=True,
        review_status="approved",
        claim_truth_confidence=0.30,
        notes=(
            "PROVISIONAL / LOW CONFIDENCE: yellow center-line style markings are "
            "common in parts of North America among other places.  Small support "
            "set for pipeline testing only; not a worldwide rule."
        ),
    ),
    ClaimVersion(
        id="claim:road:gray_paved_surface:v1",
        observation_pattern="road_region_predominantly_gray",
        geographic_scope="broad",
        diagnosticity=0.10,
        reliability=0.50,
        supports=(),
        weakens=(),
        feature_key="gray_percentage",
        production_ready=True,
        review_status="approved",
        claim_truth_confidence=0.20,
        notes=(
            "PROVISIONAL / LOW CONFIDENCE: gray paved surfaces are widespread. "
            "Empty support set — observation alone must not emit country evidence."
        ),
    ),
    ClaimVersion(
        id="claim:road:dark_road_surface:v1",
        observation_pattern="high_dark_pixel_ratio",
        geographic_scope="broad",
        diagnosticity=0.10,
        reliability=0.40,
        supports=(),
        weakens=(),
        feature_key="dark_percentage",
        production_ready=True,
        review_status="approved",
        claim_truth_confidence=0.15,
        notes=(
            "PROVISIONAL / LOW CONFIDENCE: dark surface pixels are non-diagnostic. "
            "Empty support set — no country evidence emitted."
        ),
    ),
)

_CATALOGS = {
    CLAIM_CATALOG_VERSION: ROAD_CLAIMS_V1,
}


def catalog_claims(claim_version: str = CLAIM_CATALOG_VERSION) -> Tuple[ClaimVersion, ...]:
    """Return the immutable claim catalog for a version string."""
    claims = _CATALOGS.get(claim_version)
    if claims is None:
        return ()
    return claims


def claims_for_observation(
    observation_type: str,
    claim_version: str = CLAIM_CATALOG_VERSION,
    *,
    feature_key: Optional[str] = None,
) -> Tuple[ClaimVersion, ...]:
    """Return approved production-ready claims matching an observation type."""
    del feature_key  # reserved for future feature-key matching
    return tuple(
        claim
        for claim in catalog_claims(claim_version)
        if claim.production_ready
        and claim.review_status == "approved"
        and claim.observation_pattern == observation_type
    )


def all_claim_versions(claim_version: str = CLAIM_CATALOG_VERSION) -> Sequence[ClaimVersion]:
    """Expose the full catalog for inspection / tooling."""
    return catalog_claims(claim_version)
