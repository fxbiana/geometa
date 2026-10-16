from typing import Dict, List, Sequence, Tuple

try:
    from .contracts import (
        CandidateScore,
        CandidateType,
        Evidence,
        EvidenceDirection,
        ScoreContribution,
    )
except ImportError:  # pragma: no cover - compatibility for old scripts
    from contracts import CandidateScore, CandidateType, Evidence, EvidenceDirection, ScoreContribution


def score_evidence(
    evidence: Sequence[Evidence],
    candidate_ids: Sequence[str],
    *,
    minimum_evidence: int = 1,
) -> Tuple[CandidateScore, ...]:
    """Score country candidates with traceable, non-probabilistic contributions."""
    if minimum_evidence < 1:
        raise ValueError("minimum_evidence must be positive")
    totals: Dict[str, List[ScoreContribution]] = {candidate: [] for candidate in candidate_ids}
    for item in evidence:
        if item.direction not in (EvidenceDirection.SUPPORTING, EvidenceDirection.WEAKENING):
            continue
        for candidate in candidate_ids:
            value = item.confidence * item.strength * item.reliability * item.diagnosticity
            if item.direction == EvidenceDirection.WEAKENING:
                value = -value
            totals[candidate].append(
                ScoreContribution(
                    evidence_id=item.id,
                    candidate_id=candidate,
                    value=value,
                    direction=item.direction,
                    reason=f"{item.direction.value} evidence {item.observation_id}",
                )
            )
    eligible = len(evidence) >= minimum_evidence
    ranked = sorted(
        ((candidate, sum(c.value for c in contributions), contributions) for candidate, contributions in totals.items()),
        key=lambda row: row[1],
        reverse=True,
    )
    return tuple(
        CandidateScore(
            candidate_id=candidate,
            candidate_type=CandidateType.COUNTRY,
            total=total,
            rank=index,
            eligible=eligible,
            contributions=tuple(contributions),
            inclusion_reason="qualifying evidence" if eligible else "insufficient evidence",
        )
        for index, (candidate, total, contributions) in enumerate(ranked, start=1)
    )


def meta_score(meta, country_data):
    country_clue = country_data.get(meta.feature)

    if country_clue is not None:
        country_value = country_clue["value"]
        country_weight = country_clue["weight"]

        if country_value == meta.value:
            return meta.confidence * meta.strength * country_weight

        return -meta.confidence * meta.strength * country_weight

    return 0

def score_countries(metas, country_metas):
    country_scores = {}

    for country, country_data in country_metas.items():
        total_score = 0

        for meta in metas:
            if meta.scope == "country":
                total_score += meta_score(meta, country_data)

        country_scores[country] = total_score

    ranked_scores = sorted(
        country_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return ranked_scores