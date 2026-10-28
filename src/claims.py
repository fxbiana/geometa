"""Versioned geographic claims for road and object observations.

Only approved, production-ready claim versions may emit Evidence.  Country
associations in this catalog are intentionally SMALL and marked provisional /
low-confidence — they exist to exercise the observation → evidence bridge, not
to assert calibrated geography.

The default catalog is additive: ROAD_CLAIMS_V1 plus the checked-in Plonkit
objects pack (bollards / road markings).  Pack-only and road-only catalogs
remain addressable by version string.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


CLAIM_CATALOG_VERSION = "road-claims-v1"
ROAD_CLAIMS_CORE_VERSION = "road-claims-v1-core"
PLONKIT_OBJECTS_PACK_VERSION = "plonkit-objects-v1"

_PACK_PATH = Path(__file__).resolve().parent.parent / "data" / "claims" / "plonkit_objects_v1.json"


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
            "set for pipeline testing only; not a worldwide rule.  Source: Plonk "
            "It guide https://www.plonkit.net/guide and Canada page "
            "https://www.plonkit.net/canada.  Detector-aligned sibling pattern: "
            "object_road_marking_yellow_center in plonkit-objects-v1."
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


def _as_str_tuple(value: Any) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _claim_from_pack_row(row: Mapping[str, Any]) -> ClaimVersion:
    return ClaimVersion(
        id=str(row["id"]),
        observation_pattern=str(row["observation_pattern"]),
        geographic_scope=str(row.get("geographic_scope", "country")),
        diagnosticity=float(row["diagnosticity"]),
        reliability=float(row["reliability"]),
        supports=_as_str_tuple(row.get("supports")),
        weakens=_as_str_tuple(row.get("weakens")),
        feature_key=(str(row["feature_key"]) if row.get("feature_key") is not None else None),
        production_ready=bool(row.get("production_ready", True)),
        review_status=str(row.get("review_status", "approved")),
        claim_truth_confidence=float(row.get("claim_truth_confidence", 0.0)),
        notes=str(row.get("notes") or row.get("note") or ""),
    )


def load_claim_pack(path: Path = _PACK_PATH) -> Tuple[ClaimVersion, ...]:
    """Load an on-disk claim pack JSON into ClaimVersion rows."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("claims") or []
    return tuple(_claim_from_pack_row(row) for row in rows)


def load_observation_aliases(path: Path = _PACK_PATH) -> Dict[str, str]:
    """Return observation_type aliases declared by the Plonkit objects pack."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("aliases") or {}
    return {str(src): str(dst) for src, dst in raw.items()}


PLONKIT_OBJECTS_V1: Tuple[ClaimVersion, ...] = load_claim_pack()
OBSERVATION_ALIASES: Dict[str, str] = load_observation_aliases()

# Default catalog stays under road-claims-v1 for API stability, but is additive:
# legacy road patterns plus Plonkit object patterns.
_DEFAULT_CATALOG: Tuple[ClaimVersion, ...] = ROAD_CLAIMS_V1 + PLONKIT_OBJECTS_V1

_CATALOGS: Dict[str, Tuple[ClaimVersion, ...]] = {
    CLAIM_CATALOG_VERSION: _DEFAULT_CATALOG,
    ROAD_CLAIMS_CORE_VERSION: ROAD_CLAIMS_V1,
    PLONKIT_OBJECTS_PACK_VERSION: PLONKIT_OBJECTS_V1,
}


def catalog_claims(claim_version: str = CLAIM_CATALOG_VERSION) -> Tuple[ClaimVersion, ...]:
    """Return the immutable claim catalog for a version string."""
    claims = _CATALOGS.get(claim_version)
    if claims is None:
        return ()
    return claims


def resolve_observation_pattern(observation_type: str) -> str:
    """Map Detector aliases onto canonical pack / road observation patterns."""
    return OBSERVATION_ALIASES.get(observation_type, observation_type)


def claims_for_observation(
    observation_type: str,
    claim_version: str = CLAIM_CATALOG_VERSION,
    *,
    feature_key: Optional[str] = None,
) -> Tuple[ClaimVersion, ...]:
    """Return approved production-ready claims matching an observation type.

    Unknown / unmatched observation patterns return an empty tuple.  Pack
    aliases (e.g. ``bollard_detected`` → ``object_bollard``) are resolved
    before matching.  Matching is exact on ``observation_pattern`` after alias
    resolution; generic ``object_bollard`` / ``object_road_marking`` claims keep
    empty country sets so they never invent geography.
    """
    del feature_key  # reserved for future feature-key matching
    pattern = resolve_observation_pattern(observation_type)
    return tuple(
        claim
        for claim in catalog_claims(claim_version)
        if claim.production_ready
        and claim.review_status == "approved"
        and claim.observation_pattern == pattern
    )


def all_claim_versions(claim_version: str = CLAIM_CATALOG_VERSION) -> Sequence[ClaimVersion]:
    """Expose the full catalog for inspection / tooling."""
    return catalog_claims(claim_version)
