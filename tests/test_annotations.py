import hashlib

import pytest

from src.annotations import (
    AnnotationValidationError,
    Presence,
    Visibility,
    validate_annotation_payload,
)


def valid_payload():
    return {
        "annotation_id": "a-1",
        "image_id": "pilot-001",
        "image_path": "images/compressed_dataset/X/image.jpg",
        "content_hash": hashlib.sha256(b"image").hexdigest(),
        "annotator": None,
        "image_quality": "fair",
        "interface_contamination": "possible",
        "visual_annotations": [
            {
                "feature": "road_marking",
                "feature_family": "road",
                "presence": "unknown",
                "visibility": "not_visible",
                "interpretations": [
                    {"value": "paint", "confidence": 0.4},
                    {"value": "reflection", "confidence": 0.3},
                ],
            }
        ],
    }


def test_validation_preserves_uncertainty_without_ground_truth():
    record = validate_annotation_payload(valid_payload())
    assert not hasattr(record, "country_label")
    assert record.visual_annotations[0].presence is Presence.UNKNOWN
    assert record.visual_annotations[0].visibility is Visibility.NOT_VISIBLE
    assert len(record.visual_annotations[0].interpretations) == 2


@pytest.mark.parametrize(
    "visibility",
    ("outside_frame", "obscured", "too_low_quality", "contaminated"),
)
def test_unobservable_visibility_causes_round_trip_and_require_unknown(visibility):
    payload = valid_payload()
    payload["visual_annotations"][0]["visibility"] = visibility
    record = validate_annotation_payload(payload)
    assert record.to_dict()["visual_annotations"][0]["visibility"] == visibility
    payload["visual_annotations"][0]["presence"] = "absent"
    with pytest.raises(AnnotationValidationError):
        validate_annotation_payload(payload)


def test_present_and_not_visible_is_invalid():
    payload = valid_payload()
    payload["visual_annotations"][0]["presence"] = "present"
    with pytest.raises(AnnotationValidationError):
        validate_annotation_payload(payload)


def test_absent_and_not_visible_is_invalid_and_label_is_rejected():
    payload = valid_payload()
    payload["visual_annotations"][0]["presence"] = "absent"
    with pytest.raises(AnnotationValidationError):
        validate_annotation_payload(payload)
    payload = valid_payload()
    payload["country_label"] = {"country": "Evaluation-only"}
    with pytest.raises(AnnotationValidationError):
        validate_annotation_payload(payload)


def test_hash_and_required_metadata_are_validated():
    payload = valid_payload()
    payload["content_hash"] = "not-a-hash"
    with pytest.raises(AnnotationValidationError):
        validate_annotation_payload(payload)
    payload = valid_payload()
    del payload["annotation_id"]
    with pytest.raises(AnnotationValidationError):
        validate_annotation_payload(payload)
