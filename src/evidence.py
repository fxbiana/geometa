"""Map visual observations + approved claims → Evidence records.

Evidence is emitted only when a claim matches an observation and that claim
has a non-empty supporting or weakening country set.  Pixel measurements alone
never invent geographic evidence.
"""

from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from .claims import CLAIM_CATALOG_VERSION, ClaimVersion, claims_for_observation
from .contracts import (
    CandidateScore,
    CandidateType,
    Evidence,
    EvidenceDirection,
    Observation,
    ObservationState,
    ScoreContribution,
)
from .scoring import score_evidence

# Observations that assert absence must not create geographic evidence.
_SKIP_STATES = frozenset({ObservationState.ABSENT})


def build_evidence(
    observations: Sequence[Observation],
    claim_version: str = CLAIM_CATALOG_VERSION,
) -> Tuple[Evidence, ...]:
    """Emit Evidence only for matching approved claims with country targets.

    Empty ``supports`` and ``weakens`` on a claim produce no evidence for that
    claim.  Unknown claim catalog versions yield an empty tuple.
    """
    records: List[Evidence] = []
    seen: set = set()
    for observation in observations:
        if observation.state in _SKIP_STATES:
            continue
        for claim in claims_for_observation(
            observation.observation_type,
            claim_version,
        ):
            for item in _evidence_from_claim(observation, claim):
                if item.deduplication_key in seen:
                    continue
                if item.deduplication_key is not None:
                    seen.add(item.deduplication_key)
                records.append(item)
    return tuple(records)


def _evidence_from_claim(
    observation: Observation,
    claim: ClaimVersion,
) -> List[Evidence]:
    if not claim.production_ready or claim.review_status != "approved":
        return []
    records: List[Evidence] = []
    for countries, direction in (
        (claim.supports, EvidenceDirection.SUPPORTING),
        (claim.weakens, EvidenceDirection.WEAKENING),
    ):
        if not countries:
            continue
        dedupe = f"{observation.id}:{claim.id}:{direction.value}"
        records.append(
            Evidence(
                id=f"{observation.analysis_id}:evidence:{claim.id}:{direction.value}",
                analysis_id=observation.analysis_id,
                observation_id=observation.id,
                value={
                    "observed": observation.value,
                    "countries": countries,
                    "claim_id": claim.id,
                },
                confidence=observation.confidence,
                strength=min(claim.diagnosticity, claim.reliability),
                reliability=claim.reliability,
                diagnosticity=claim.diagnosticity,
                geographic_scope=claim.geographic_scope,
                direction=direction,
                source_id=observation.source_id,
                region=observation.region,
                claim_version_id=claim.id,
                deduplication_key=dedupe,
            )
        )
    return records


def rank_candidates(evidence: Sequence[Evidence]) -> Tuple[CandidateScore, ...]:
    """Score each applicable country using only evidence that targets it.

    ``score_evidence`` applies every evidence item to every candidate it is
    given, so country sets must be scored separately and then re-ranked.
    """
    by_country: Dict[str, List[Evidence]] = defaultdict(list)
    for item in evidence:
        countries = ()
        if isinstance(item.value, dict):
            countries = tuple(item.value.get("countries") or ())
        for country in countries:
            by_country[country].append(item)

    if not by_country:
        return ()

    scored: List[CandidateScore] = []
    for country in sorted(by_country):
        country_scores = score_evidence(tuple(by_country[country]), (country,))
        scored.extend(country_scores)

    ranked = sorted(scored, key=lambda row: row.total, reverse=True)
    return tuple(
        CandidateScore(
            candidate_id=row.candidate_id,
            candidate_type=CandidateType.COUNTRY,
            total=row.total,
            rank=index,
            eligible=row.eligible,
            contributions=tuple(
                ScoreContribution(
                    evidence_id=c.evidence_id,
                    candidate_id=c.candidate_id,
                    value=c.value,
                    direction=c.direction,
                    reason=c.reason,
                    calculation_version=c.calculation_version,
                )
                for c in row.contributions
            ),
            inclusion_reason=row.inclusion_reason,
        )
        for index, row in enumerate(ranked, start=1)
    )
