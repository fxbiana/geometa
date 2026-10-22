"""Legacy clue catalog facade over the versioned road claim catalog.

Prefer ``src.claims`` for new code.  This module keeps the old ``CLUES`` shape
for prototype callers while pointing at claim-backed metadata.
"""

from .claims import CLAIM_CATALOG_VERSION, all_claim_versions, claims_for_observation


def _clues_from_claims() -> dict:
    road = {}
    for claim in all_claim_versions(CLAIM_CATALOG_VERSION):
        key = claim.feature_key or claim.observation_pattern
        road[key] = {
            "description": claim.notes or claim.observation_pattern,
            "observation_pattern": claim.observation_pattern,
            "diagnosticity": claim.diagnosticity,
            "reliability": claim.reliability,
            "geographic_scope": claim.geographic_scope,
            "supports": list(claim.supports),
            "weakens": list(claim.weakens),
            "claim_version_id": claim.id,
            "provisional": True,
            "evidence": {},
        }
    return {"road": road}


CLUES = _clues_from_claims()


def get_clue(category, clue_name):
    return CLUES.get(category, {}).get(clue_name)


def describe_clue(category, clue_name):
    clue = get_clue(category, clue_name)
    if clue is None:
        return None
    return clue["description"]


def approved_claims_for(observation_type: str, claim_version: str = CLAIM_CATALOG_VERSION):
    """Thin wrapper for callers that still import knowledge."""
    return claims_for_observation(observation_type, claim_version)
