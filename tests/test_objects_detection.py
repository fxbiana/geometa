"""Smoke tests for the YOLO-World object detector (mocked; no weight download)."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from src.contracts import ObservationState, RegionType
from src.detection import detect_objects as detect_objects_facade
from src.features.objects import (
    OBJECT_CLASS_LABELS,
    OBSERVATION_TYPE_BY_LABEL,
    ObjectAnalysis,
    detect_objects,
    reset_model_cache,
)


FIXTURE_IMAGE = Path(__file__).resolve().parents[1] / "images" / "commerce_california.png"

# Observation / detection modules must stay geography-free (claims own mapping).
_GEO_PATTERN = re.compile(
    r"\b("
    r"country|countries|nation|iso[_ -]?3166|geographic_scope|"
    r"united[ _-]?states|canada|brazil|denmark|ghana|japan|ireland|peru|"
    r"australia|greece|tunisia|malaysia|turkey|alaska|california|"
    r"candidate_id"
    r")\b",
    re.IGNORECASE,
)
_ISO_ALPHA2_ASSIGNMENT = re.compile(r"""["'][A-Z]{2}["']""")


def _fake_infer(image, **_kwargs):
    w, h = image.size
    return [
        ("bollard", 0.91, (10, h // 2, 40, h // 2 + 80)),
        ("sign", 0.77, (w // 2, 20, w // 2 + 60, 80)),
        ("pole", 0.55, (w - 50, 30, w - 20, h - 10)),
        ("road marking", 0.62, (w // 4, 2 * h // 3, 3 * w // 4, h - 5)),
        ("guardrail", 0.48, (5, 2 * h // 3, w // 5, h - 5)),
    ]


def test_object_class_prompt_labels_are_exact():
    assert OBJECT_CLASS_LABELS == (
        "bollard",
        "guardrail",
        "road marking",
        "sign",
        "pole",
    )
    assert set(OBSERVATION_TYPE_BY_LABEL.values()) == {
        "object_bollard",
        "object_guardrail",
        "object_road_marking",
        "object_sign",
        "object_pole",
    }


def test_detect_objects_mocked_yolo_returns_contract_observations():
    assert FIXTURE_IMAGE.is_file(), f"missing fixture {FIXTURE_IMAGE}"
    with Image.open(FIXTURE_IMAGE) as image:
        image.load()
        result = detect_objects(
            image.convert("RGB"),
            source_id="fixture",
            analysis_id="a1",
            infer_fn=_fake_infer,
            confidence_threshold=0.25,
        )

    assert isinstance(result, ObjectAnalysis)
    assert len(result.observations) == 5
    assert len(result.measurements) == 5
    types = {obs.observation_type for obs in result.observations}
    assert types == {
        "object_bollard",
        "object_guardrail",
        "object_road_marking",
        "object_sign",
        "object_pole",
    }
    for obs in result.observations:
        assert obs.state is ObservationState.POSITIVE
        assert obs.region.region_type is RegionType.BOUNDING_BOX
        assert obs.region.coordinates is not None
        x1, y1, x2, y2 = obs.region.coordinates
        assert x2 > x1 and y2 > y1
        assert 0.0 <= obs.confidence <= 1.0
        assert obs.supporting_measurement_ids
        assert obs.value is True


def test_detect_objects_facade_and_missing_weights_degrade_empty(monkeypatch):
    reset_model_cache()

    def boom_load(_name="yolov8s-world.pt"):
        return None

    monkeypatch.setattr("src.features.objects._load_yolo_world", boom_load)
    image = Image.new("RGB", (64, 64), (80, 80, 80))
    result = detect_objects(image, source_id="s", analysis_id="a")
    assert result.observations == ()
    assert result.measurements == ()

    facade = detect_objects_facade(None)
    assert facade.observations == ()
    assert facade.measurements == ()


def test_detection_and_objects_modules_contain_no_geography_strings():
    root = Path(__file__).resolve().parents[1] / "src"
    for rel in ("detection.py", "features/objects.py"):
        text = (root / rel).read_text(encoding="utf-8")
        matches = _GEO_PATTERN.findall(text)
        iso_hits = _ISO_ALPHA2_ASSIGNMENT.findall(text)
        assert matches == [], f"{rel} contains geography tokens: {matches}"
        assert iso_hits == [], f"{rel} contains ISO-like string literals: {iso_hits}"
