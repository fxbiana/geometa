"""Smoke tests for sign-crop writing-system observations."""

from pathlib import Path

from PIL import Image

from src.contracts import ObservationState, RegionType
from src.features.script import (
    KNOWN_WRITING_SYSTEMS,
    NullOcrBackend,
    SCRIPT_OBSERVATION_TYPE,
    analyze_script,
    classify_writing_system,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_classify_hangul_positive():
    value, state, confidence = classify_writing_system("한국도로공사")
    assert value == "hangul"
    assert state is ObservationState.POSITIVE
    assert confidence > 0.5


def test_classify_each_known_system():
    samples = {
        "hangul": "서울특별시",
        "thai": "กรุงเทพมหานคร",
        "cyrillic": "Москва",
        "kana": "あいうエオ",
        "latin": "STOP AHEAD",
    }
    for expected, text in samples.items():
        value, state, _ = classify_writing_system(text)
        assert value == expected, text
        assert state is ObservationState.POSITIVE
        assert expected in KNOWN_WRITING_SYSTEMS


def test_classify_empty_and_mixed_are_unknown_ambiguous():
    empty_value, empty_state, empty_conf = classify_writing_system("")
    assert empty_value == "unknown"
    assert empty_state is ObservationState.AMBIGUOUS
    assert empty_conf == 0.0

    mixed_value, mixed_state, _ = classify_writing_system("한국 STOP Москва")
    assert mixed_value == "unknown"
    assert mixed_state is ObservationState.AMBIGUOUS


def test_analyze_script_smoke_hangul_fixture_with_mock_ocr():
    """CI-safe smoke: real Hangul crop + mockable OCR backend (no Paddle/GPU)."""
    path = FIXTURES / "sign_crop_hangul.png"
    assert path.is_file()
    image = Image.open(path)
    image.load()

    observation = analyze_script(
        image,
        source_id="sign_crop_hangul.png",
        analysis_id="analysis:script-smoke",
        ocr_backend=lambda _img: "한국",
    )

    assert observation.observation_type == SCRIPT_OBSERVATION_TYPE
    assert observation.value == "hangul"
    assert observation.state is ObservationState.POSITIVE
    assert observation.region.region_type is RegionType.FULL_IMAGE
    assert observation.source_id == "sign_crop_hangul.png"
    assert observation.analysis_id == "analysis:script-smoke"
    # Module must not invent country codes.
    assert observation.value not in {"KR", "KP", "US", "TH", "JP", "RU"}


def test_analyze_script_latin_fixture_via_ocr_text():
    path = FIXTURES / "sign_crop_latin.png"
    image = Image.open(path)
    image.load()
    observation = analyze_script(
        image,
        source_id="sign_crop_latin.png",
        analysis_id="analysis:latin",
        ocr_text="STOP",
        region_type=RegionType.BOUNDING_BOX,
    )
    assert observation.observation_type == SCRIPT_OBSERVATION_TYPE
    assert observation.value == "latin"
    assert observation.region.region_type is RegionType.BOUNDING_BOX
    assert observation.region.coordinates == (0, 0, image.size[0], image.size[1])


def test_analyze_script_null_backend_is_ambiguous_unknown():
    image = Image.new("RGB", (32, 32), "white")
    observation = analyze_script(
        image,
        source_id="blank.png",
        analysis_id="analysis:blank",
        ocr_backend=NullOcrBackend(),
    )
    assert observation.observation_type == SCRIPT_OBSERVATION_TYPE
    assert observation.value == "unknown"
    assert observation.state is ObservationState.AMBIGUOUS
