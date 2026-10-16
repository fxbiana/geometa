from PIL import Image

from src.evaluation_harness import (
    ManifestExample,
    evaluate,
    extract_predictions,
    load_manifest,
    split_manifest,
)


def _write_image(path, color):
    image = Image.new("RGB", (8, 8), color)
    image.save(path, format="PNG")


def test_split_is_stable_and_keeps_labels_in_manifest_only(tmp_path):
    examples = []
    for index, label in enumerate(("A", "A", "A", "B", "B", "B")):
        path = tmp_path / f"{index}.png"
        _write_image(path, (50 + index * 20,) * 3)
        examples.append(ManifestExample(str(index), str(path), label))

    first = split_manifest(examples, seed=7)
    second = split_manifest(tuple(reversed(examples)), seed=7)
    assert first == second
    prediction = extract_predictions(first["development"], "development")[0]
    assert not hasattr(prediction, "label")
    assert prediction.features


def test_evaluation_is_reproducible_and_reports_all_baselines(tmp_path):
    examples = []
    for index, label in enumerate(("A", "A", "A", "B", "B", "B")):
        path = tmp_path / f"{index}.png"
        _write_image(path, (50 + index * 20,) * 3)
        examples.append(ManifestExample(str(index), str(path), label))

    first = evaluate(examples, seed=11)
    second = evaluate(examples, seed=11)
    assert first == second
    assert set(first["baselines"]) == {"random", "class_prior", "road_measurement_centroid"}
    assert first["inputs"]["ground_truth_used_during_extraction"] is False
    assert "gray_percentage" in first["feature_prevalence_and_coverage"]
    assert first["split"]["development"] + first["split"]["validation"] == 6


def test_loads_approved_subset_manifest_shape(tmp_path):
    image_root = tmp_path / "historical-images"
    image_root.mkdir()
    image_path = image_root / "sample.png"
    _write_image(image_path, (100, 100, 100))
    manifest = tmp_path / "approved-external-dataset-subset-manifest.json"
    manifest.write_text(
        '{"dataset":{"local_root":"historical-images"},'
        '"entries":[{"id":"known-1","relative_path":"sample.png",'
        '"country":"Exampleland","sha256":"abc123"}]}',
        encoding="utf-8",
    )

    examples = load_manifest(manifest)

    assert examples == (
        ManifestExample("known-1", str(image_path), "Exampleland", "abc123"),
    )
