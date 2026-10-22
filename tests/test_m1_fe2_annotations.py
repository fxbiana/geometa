import json

import pytest

from src.annotations import (
    AnnotationValidationError,
    load_annotations,
    validate_annotation_payload,
)
from tools.manage_m1_fe2_annotations import generate_template, validate


def test_generated_template_has_100_needs_review_records_without_labels(tmp_path):
    manifest = tmp_path / "manifest.json"
    entries = [
        {
            "id": "pilot-{0:03d}".format(index),
            "relative_path": "Country/image-{0}.jpg".format(index),
            "content_hash": "{0:064x}".format(index),
        }
        for index in range(1, 101)
    ]
    manifest.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    output = tmp_path / "annotations.jsonl"
    generate_template(manifest, output)
    records = validate(output)
    assert len(records) == 100
    assert all(record.review_status == "needs_review" for record in records)
    assert all(record.annotator is None for record in records)
    assert all("country_label" not in record.to_dict() for record in records)


def test_jsonl_duplicate_ids_are_rejected(tmp_path):
    row = {
        "annotation_id": "a",
        "image_id": "i",
        "image_path": "image.jpg",
        "content_hash": "a" * 64,
        "annotator": None,
        "image_quality": "unknown",
        "interface_contamination": "unknown",
    }
    path = tmp_path / "annotations.jsonl"
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(AnnotationValidationError, match="unique"):
        load_annotations(str(path))


def test_feature_families_and_separate_road_marker_observations():
    from src.annotations import FeatureFamily

    payload = {
        "annotation_id": "a",
        "image_id": "i",
        "image_path": "image.jpg",
        "content_hash": "a" * 64,
        "review_status": "needs_review",
        "image_quality": "unknown",
        "interface_contamination": "unknown",
        "visual_annotations": [
            {
                "feature_family": FeatureFamily.ROAD.value,
                "feature": "road_marking",
                "presence": "unknown",
                "visibility": "outside_frame",
            },
            {
                "feature_family": FeatureFamily.ROAD.value,
                "feature": "raised_marker",
                "presence": "unknown",
                "visibility": "obscured",
            },
        ],
    }
    record = validate_annotation_payload(payload)
    assert [item.feature for item in record.visual_annotations] == [
        "road_marking",
        "raised_marker",
    ]
