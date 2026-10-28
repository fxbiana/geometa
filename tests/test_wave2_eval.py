"""Wave 2 evaluation harness tests.

Unit path: injected observations + claim catalog (always runs).
Integration path: live detectors / pipeline — skipped until objects/script land.
Failing-closed: any predicted country without an approved matching claim fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple

import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.claims import ClaimVersion, claims_for_observation
from src.wave2_eval import (
    OBJECT_OBSERVATION_TYPES,
    assert_countries_have_claims,
    default_fixture_pack,
    evaluate_injected,
    evaluate_via_pipeline,
    format_report_summary,
    load_wave2_pack,
    object_precision_counts,
    objects_detector_available,
    print_report,
    script_detector_available,
    unjustified_countries,
    wave2_detectors_available,
)

client = TestClient(app)
FIXTURE_PACK = default_fixture_pack()


@dataclass(frozen=True)
class _StubClaim:
    id: str
    observation_pattern: str
    supports: Tuple[str, ...]
    weakens: Tuple[str, ...] = ()
    production_ready: bool = True
    review_status: str = "approved"


WAVE2_STUB_CLAIMS: Tuple[_StubClaim, ...] = (
    _StubClaim("claim:objects:bollard:v1", "bollard_present", ("IE",)),
    _StubClaim("claim:objects:utility_pole:v1", "utility_pole_present", ("JP",)),
    _StubClaim(
        "claim:script:cjk:v1",
        "cjk_script_signage",
        ("JP", "KR", "CN"),
    ),
    _StubClaim(
        "claim:script:latin:v1",
        "latin_script_signage",
        (),
    ),
)


def _stub_claim_lookup(observation_type: str) -> Sequence[_StubClaim | ClaimVersion]:
    """Prefer production catalog matches; fall back to Wave 2 stub claims."""
    live = claims_for_observation(observation_type)
    if live:
        return live
    return tuple(
        claim
        for claim in WAVE2_STUB_CLAIMS
        if claim.observation_pattern == observation_type
        and claim.production_ready
        and claim.review_status == "approved"
    )


def test_fixture_pack_layout_exists():
    pack_version, examples = load_wave2_pack(FIXTURE_PACK)
    assert pack_version == "wave2-eval-v1"
    assert len(examples) >= 6
    ids = {example.example_id for example in examples}
    assert {"yellow_road", "bollard_stub", "cjk_script_stub"} <= ids
    for example in examples:
        assert example.image_path.is_file(), example.image_path
        expected = FIXTURE_PACK / "expected" / f"{example.example_id}.json"
        assert expected.is_file(), expected


def test_object_precision_counts_ignore_non_object_types():
    tp, fp, fn = object_precision_counts(
        predicted=["bollard_present", "possible_yellow_marking", "utility_pole_present"],
        expected=["bollard_present", "cjk_script_signage"],
    )
    # utility_pole_present is FP (object); cjk is not an object type so not FN here
    assert "bollard_present" in OBJECT_OBSERVATION_TYPES
    assert tp == 1
    assert fp == 1
    assert fn == 0


def test_country_without_claim_fails_closed():
    observations = ("bollard_present",)
    predicted = ("IE", "XX")
    bad = unjustified_countries(predicted, observations, _stub_claim_lookup)
    assert bad == ("XX",)
    with pytest.raises(AssertionError, match="country without claim"):
        assert_countries_have_claims(predicted, observations, _stub_claim_lookup)


def test_country_without_claim_passes_when_justified():
    assert_countries_have_claims(
        ("IE",),
        ("bollard_present",),
        _stub_claim_lookup,
    )


def test_injected_pack_reports_object_precision_and_top_country(capsys):
    pack_version, examples = load_wave2_pack(FIXTURE_PACK)
    predictions = {
        "yellow_road": {
            "observations": ["possible_yellow_marking"],
            "countries": ["US", "CA"],
        },
        "gray_road": {
            "observations": ["road_region_predominantly_gray"],
            "countries": [],
        },
        "bollard_stub": {
            "observations": ["bollard_present"],
            "countries": ["IE"],
        },
        "utility_pole_stub": {
            "observations": ["utility_pole_present"],
            "countries": ["JP"],
        },
        "cjk_script_stub": {
            "observations": ["cjk_script_signage"],
            "countries": ["JP", "KR", "CN"],
        },
        "latin_script_stub": {
            "observations": ["latin_script_signage"],
            "countries": [],
        },
    }
    report = evaluate_injected(
        pack_version,
        examples,
        predictions,
        claim_lookup=_stub_claim_lookup,
    )
    print_report(report)
    captured = capsys.readouterr().out
    assert "precision for objects:" in captured
    assert "top-country accuracy:" in captured
    assert report.object_precision == 1.0
    assert report.top_country_accuracy == 1.0
    assert report.country_without_claim_violations == ()
    for case in report.cases:
        assert_countries_have_claims(
            case.predicted_countries,
            case.predicted_observations,
            _stub_claim_lookup,
        )


def test_injected_report_fails_when_country_lacks_claim():
    pack_version, examples = load_wave2_pack(FIXTURE_PACK)
    predictions = {
        example.example_id: {
            "observations": list(example.expected_observations),
            "countries": list(example.expected_countries),
        }
        for example in examples
    }
    predictions["bollard_stub"]["countries"] = ["IE", "ZZ"]
    report = evaluate_injected(
        pack_version,
        examples,
        predictions,
        claim_lookup=_stub_claim_lookup,
    )
    assert report.country_without_claim_violations
    assert any("ZZ" in item for item in report.country_without_claim_violations)
    bollard = next(case for case in report.cases if case.example_id == "bollard_stub")
    with pytest.raises(AssertionError, match="country without claim"):
        assert_countries_have_claims(
            bollard.predicted_countries,
            bollard.predicted_observations,
            _stub_claim_lookup,
        )


def test_format_report_summary_labels():
    text = format_report_summary(
        object_precision=0.5,
        object_recall=1.0,
        top_country_accuracy=0.25,
        violations=("case:XX",),
        case_count=4,
    )
    assert "precision for objects: 0.500" in text
    assert "top-country accuracy: 0.250" in text
    assert "country without claim: case:XX" in text


def test_pipeline_road_fixtures_join_claims_without_hardcoding(capsys):
    """Road stills exercise analyze_source; object stills expected empty until detectors land."""
    pack_version, examples = load_wave2_pack(FIXTURE_PACK)
    road_examples = tuple(ex for ex in examples if ex.family == "road")
    report = evaluate_via_pipeline(road_examples, pack_version=pack_version)
    print_report(report)
    out = capsys.readouterr().out
    assert "precision for objects:" in out
    assert "top-country accuracy:" in out
    for case in report.cases:
        assert_countries_have_claims(
            case.predicted_countries,
            case.predicted_observations,
            claims_for_observation,
        )
    yellow = next(case for case in report.cases if case.example_id == "yellow_road")
    assert "possible_yellow_marking" in yellow.predicted_observations
    assert yellow.top_country in {"US", "CA"}
    assert set(yellow.predicted_countries) <= {"US", "CA"}


def test_post_v1_analyses_on_wave2_still():
    image_path = FIXTURE_PACK / "stills" / "yellow_road.png"
    response = client.post(
        "/v1/analyses",
        files={"file": ("yellow_road.png", image_path.read_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"completed", "insufficient_evidence"}
    assert body["source_hash"]
    observation_types = [item["observation_type"] for item in body["observations"]]
    countries = [item["candidate_id"] for item in body.get("candidates", [])]
    assert_countries_have_claims(countries, observation_types, claims_for_observation)


@pytest.mark.wave2_integration
def test_wave2_object_script_integration_when_detectors_available(capsys):
    if not wave2_detectors_available():
        pytest.skip(
            "Wave 2 detectors unavailable "
            f"(objects={objects_detector_available()}, script={script_detector_available()})"
        )
    pack_version, examples = load_wave2_pack(FIXTURE_PACK)
    target = tuple(ex for ex in examples if ex.family in {"objects", "script"})
    report = evaluate_via_pipeline(target, pack_version=pack_version)
    print_report(report)
    assert "precision for objects:" in report.printed_summary
    assert report.country_without_claim_violations == ()
    for case in report.cases:
        assert_countries_have_claims(
            case.predicted_countries,
            case.predicted_observations,
            claims_for_observation,
        )
