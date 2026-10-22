from src.claims import CLAIM_CATALOG_VERSION, claims_for_observation
from src.contracts import (
    EvidenceDirection,
    ImageRegion,
    Observation,
    ObservationState,
    RegionType,
)
from src.evidence import build_evidence, rank_candidates


def _observation(
    observation_type: str,
    *,
    state: ObservationState = ObservationState.POSITIVE,
    analysis_id: str = "analysis:test",
) -> Observation:
    return Observation(
        id=f"{analysis_id}:observation:{observation_type}",
        analysis_id=analysis_id,
        source_id="fixture.png",
        region=ImageRegion("fixture.png", RegionType.BOTTOM_THIRD, (0, 4, 6, 6)),
        observation_type=observation_type,
        value=True,
        confidence=0.8,
        state=state,
        supporting_measurement_ids=(f"{analysis_id}:measurement:stub",),
    )


def test_build_evidence_empty_when_no_matching_claims():
    observations = (_observation("no_strong_road_color_characteristics", state=ObservationState.ABSENT),)
    assert build_evidence(observations) == ()


def test_build_evidence_skips_claims_with_empty_supports():
    observations = (_observation("road_region_predominantly_gray"),)
    assert claims_for_observation("road_region_predominantly_gray")[0].supports == ()
    assert build_evidence(observations) == ()


def test_build_evidence_emits_for_yellow_marking_match():
    observations = (
        _observation("possible_yellow_marking", state=ObservationState.AMBIGUOUS),
    )
    evidence = build_evidence(observations, CLAIM_CATALOG_VERSION)
    assert len(evidence) == 1
    item = evidence[0]
    assert item.direction is EvidenceDirection.SUPPORTING
    assert item.claim_version_id == "claim:road:yellow_center_line:v1"
    assert item.value["countries"] == ("US", "CA")
    assert item.observation_id == observations[0].id


def test_build_evidence_unknown_catalog_emits_nothing():
    observations = (_observation("possible_yellow_marking", state=ObservationState.AMBIGUOUS),)
    assert build_evidence(observations, "claims-does-not-exist") == ()


def test_rank_candidates_only_scores_targeted_countries():
    observations = (
        _observation("possible_yellow_marking", state=ObservationState.AMBIGUOUS),
    )
    evidence = build_evidence(observations)
    candidates = rank_candidates(evidence)
    assert candidates
    ids = {c.candidate_id for c in candidates}
    assert ids == {"US", "CA"}
    assert all(c.eligible for c in candidates)
    assert all(c.contributions for c in candidates)
    assert candidates[0].rank == 1
    assert sum(c.value for c in candidates[0].contributions) == candidates[0].total
