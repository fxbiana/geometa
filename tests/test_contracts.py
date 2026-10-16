from io import BytesIO

from PIL import Image

from src.contracts import (
    AnalysisResult,
    AnalysisStatus,
    Availability,
    Evidence,
    EvidenceDirection,
    ExplanationInput,
    ImageRegion,
    SourceInput,
    RegionType,
)
from src.features.road import analyze_road
from src.detection import meta_detection
from src.reasoning import explain
from src.scoring import score_evidence
from src.source import source_hash, validate_source


def image_bytes(color=(100, 100, 100), size=(6, 6)):
    image = Image.new("RGB", size, color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_source_validation_hashes_and_records_dimensions():
    data = image_bytes()
    result = validate_source(SourceInput(data, "fixture.png"))
    assert result.valid
    assert result.availability is Availability.AVAILABLE
    assert result.content_hash == source_hash(data)
    assert (result.width, result.height, result.format) == (6, 6, "PNG")


def test_invalid_source_is_unavailable_and_still_hashed():
    data = b"not an image"
    result = validate_source(SourceInput(data, "bad.bin"))
    assert not result.valid
    assert result.availability is Availability.UNAVAILABLE
    assert result.content_hash == source_hash(data)


def test_road_analysis_preserves_measurement_to_observation_provenance():
    result = analyze_road(Image.new("RGB", (6, 6), (100, 100, 100)), source_id="s", analysis_id="a")
    assert result.measurements
    assert result.observations
    measurement_ids = {item.id for item in result.measurements}
    assert all(set(item.supporting_measurement_ids) <= measurement_ids for item in result.observations)
    assert all(item.source_id == "s" and item.analysis_id == "a" for item in result.measurements)


def test_candidate_contributions_sum_to_candidate_total():
    evidence = Evidence(
        id="e1",
        analysis_id="a",
        observation_id="o1",
        value=True,
        confidence=1,
        strength=0.5,
        reliability=1,
        diagnosticity=1,
        geographic_scope="country",
        direction=EvidenceDirection.SUPPORTING,
        source_id="s",
        region=ImageRegion("s", RegionType.BOTTOM_THIRD),
    )
    candidates = score_evidence((evidence,), ("country-a",))
    assert candidates[0].total == sum(item.value for item in candidates[0].contributions)


def test_explanation_returns_recorded_analysis_without_new_evidence():
    result = AnalysisResult("a", "s", "hash", AnalysisStatus.INSUFFICIENT_EVIDENCE)
    explanation = explain(ExplanationInput(result))
    assert explanation.analysis_id == "a"
    assert explanation.evidence == ()


def test_meta_detection_does_not_return_input_independent_hardcoded_metas():
    assert meta_detection(Image.new("RGB", (6, 6), (100, 100, 100))) == []
    assert meta_detection(Image.new("RGB", (6, 6), (255, 0, 0))) == []
