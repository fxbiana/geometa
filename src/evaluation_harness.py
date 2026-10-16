"""Read-only, reproducible evaluation of the exploratory road features.

This module intentionally does not call the production scoring path.  It
extracts measurements from image inputs first, then joins labels only in the
evaluation stage.  The manifest is an external input and is never rewritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image

from .features.road import RoadAnalysis, analyze_road

FEATURES = (
    "average_brightness",
    "gray_percentage",
    "dark_percentage",
    "bright_percentage",
    "white_percentage",
    "yellow_percentage",
)
OBSERVATION_FEATURES = {
    "road_region_predominantly_gray": "gray_percentage",
    "possible_yellow_marking": "yellow_percentage",
    "high_dark_pixel_ratio": "dark_percentage",
    "large_white_pixel_ratio": "white_percentage",
}


@dataclass(frozen=True)
class ManifestExample:
    example_id: str
    image_path: str
    label: str
    content_hash: str | None = None


@dataclass(frozen=True)
class PredictionRecord:
    """Prediction inputs and outputs; deliberately contains no ground truth."""

    example_id: str
    image_path: str
    split: str
    features: Mapping[str, float] | None
    observations: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True)
class JoinedRecord:
    example_id: str
    split: str
    label: str
    prediction: str | None
    ranking: tuple[str, ...]
    error: str | None


def _field(row: Mapping[str, Any], names: Sequence[str]) -> str | None:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def load_manifest(path: str | Path) -> tuple[ManifestExample, ...]:
    """Load CSV, JSON, or JSONL manifests without changing them.

    Required concepts are an image path (``image_path``/``path``/``filename``)
    and a country label (``country``/``label``/``target``).
    """
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            rows: Iterable[Mapping[str, Any]] = csv.DictReader(handle)
            return _manifest_rows(rows, path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        if isinstance(payload, dict) and "entries" in payload:
            dataset = payload.get("dataset", {})
            if not isinstance(dataset, dict):
                raise ValueError("manifest dataset metadata must be an object")
            local_root = dataset.get("local_root")
            if not local_root:
                raise ValueError("subset manifest dataset.local_root is required")
            root = Path(str(local_root))
            if not root.is_absolute():
                root = path.parent / root
            root = root.resolve()
            rows = []
            for entry in payload["entries"]:
                if not isinstance(entry, dict):
                    raise ValueError("subset manifest entries must be objects")
                row = dict(entry)
                relative_path = _field(row, ("relative_path",))
                if not relative_path:
                    raise ValueError("subset manifest entries require relative_path")
                row["image_path"] = str(root / relative_path)
                rows.append(row)
        else:
            rows = payload.get("examples", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("manifest must contain a list of examples")
    return _manifest_rows(rows, path)


def _manifest_rows(rows: Iterable[Mapping[str, Any]], manifest_path: Path) -> tuple[ManifestExample, ...]:
    examples = []
    for index, row in enumerate(rows):
        image_path = _field(row, ("image_path", "path", "filename", "image"))
        label = _field(row, ("country", "label", "target"))
        if not image_path or not label:
            raise ValueError(f"manifest row {index + 1} needs image path and country label")
        resolved = Path(image_path)
        if not resolved.is_absolute():
            resolved = manifest_path.parent / resolved
        example_id = _field(row, ("example_id", "id")) or f"example-{index:05d}"
        content_hash = _field(row, ("sha256", "content_hash", "input_hash", "hash"))
        examples.append(ManifestExample(example_id, str(resolved), label, content_hash))
    if not examples:
        raise ValueError("manifest contains no examples")
    if len({item.example_id for item in examples}) != len(examples):
        raise ValueError("manifest example IDs must be unique")
    return tuple(examples)


def split_manifest(
    examples: Sequence[ManifestExample],
    *,
    validation_fraction: float = 0.2,
    seed: int = 20261016,
) -> dict[str, tuple[ManifestExample, ...]]:
    """Make a stable, approximately stratified split using IDs, not row order."""
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between zero and one")
    by_label: dict[str, list[ManifestExample]] = defaultdict(list)
    for example in examples:
        by_label[example.label].append(example)
    development: list[ManifestExample] = []
    validation: list[ManifestExample] = []
    for label in sorted(by_label):
        items = sorted(
            by_label[label],
            key=lambda item: hashlib.sha256(f"{seed}:{item.example_id}".encode()).hexdigest(),
        )
        count = max(1, round(len(items) * validation_fraction)) if len(items) > 1 else 0
        validation.extend(items[:count])
        development.extend(items[count:])
    return {
        "development": tuple(sorted(development, key=lambda item: item.example_id)),
        "validation": tuple(sorted(validation, key=lambda item: item.example_id)),
    }


def extract_predictions(
    examples: Sequence[ManifestExample], split: str
) -> tuple[PredictionRecord, ...]:
    """Extract road measurements from inputs only; labels are not passed on."""
    records = []
    for example in examples:
        try:
            with Image.open(example.image_path) as image:
                result: RoadAnalysis = analyze_road(
                    image, source_id=example.example_id, analysis_id=example.example_id
                )
            records.append(
                PredictionRecord(
                    example.example_id,
                    example.image_path,
                    split,
                    {item.feature: item.value for item in result.measurements},
                    tuple(item.observation_type for item in result.observations),
                )
            )
        except (OSError, ValueError) as exc:
            records.append(PredictionRecord(example.example_id, example.image_path, split, None, (), str(exc)))
    return tuple(records)


def _predict_centroid(record: PredictionRecord, centroids: Mapping[str, Mapping[str, float]]) -> tuple[str | None, tuple[str, ...]]:
    if record.features is None or not centroids:
        return None, ()
    distances = []
    for label, centroid in centroids.items():
        distance = sum((record.features[name] - centroid[name]) ** 2 for name in FEATURES)
        distances.append((distance, label))
    distances.sort()
    return distances[0][1], tuple(label for _, label in distances)


def _centroids(records: Sequence[PredictionRecord], labels: Mapping[str, str]) -> dict[str, dict[str, float]]:
    values: dict[str, list[Mapping[str, float]]] = defaultdict(list)
    for record in records:
        if record.features is not None and record.example_id in labels:
            values[labels[record.example_id]].append(record.features)
    return {
        label: {name: sum(item[name] for item in rows) / len(rows) for name in FEATURES}
        for label, rows in values.items()
    }


def _stable_unit(seed: int, example_id: str) -> float:
    digest = hashlib.sha256(f"{seed}:{example_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _random_label(labels: Sequence[str], unit: float) -> str:
    return labels[min(int(unit * len(labels)), len(labels) - 1)]


def _prior_label(prior: Mapping[str, int], unit: float) -> str:
    target = unit * sum(prior.values())
    for label, count in sorted(prior.items()):
        target -= count
        if target < 0:
            return label
    return sorted(prior)[-1]


def _metrics(rows: Sequence[JoinedRecord], classes: Sequence[str], k: int = 3) -> dict[str, Any]:
    eligible = [row for row in rows if row.ranking]
    correct = sum(row.prediction == row.label for row in eligible)
    top_k = sum(row.label in row.ranking[:k] for row in eligible)
    ranks = [row.ranking.index(row.label) + 1 for row in eligible if row.label in row.ranking]
    denominator = len(rows)
    return {
        "examples": denominator,
        "eligible_rankings": len(eligible),
        "coverage": len(eligible) / denominator if denominator else 0.0,
        "top_1_accuracy": correct / len(eligible) if eligible else None,
        "top_k": k,
        "top_k_coverage": top_k / denominator if denominator else 0.0,
        "actual_rank_mean": sum(ranks) / len(ranks) if ranks else None,
        "abstentions": sum(row.prediction is None and row.error is None for row in rows),
        "technical_failures": sum(row.error is not None for row in rows),
        "class_count": len(classes),
    }


def evaluate(
    manifest: Sequence[ManifestExample],
    *,
    validation_fraction: float = 0.2,
    seed: int = 20261016,
    dataset_version: str = "external-exploratory",
) -> dict[str, Any]:
    """Run baselines and the road diagnostic, returning JSON-serializable data."""
    splits = split_manifest(manifest, validation_fraction=validation_fraction, seed=seed)
    all_predictions = extract_predictions(
        splits["development"], "development"
    ) + extract_predictions(splits["validation"], "validation")
    by_id = {item.example_id: item for item in all_predictions}
    labels = {item.example_id: item.label for item in manifest}
    classes = tuple(sorted(set(labels.values())))
    development = [by_id[item.example_id] for item in splits["development"]]
    validation = [by_id[item.example_id] for item in splits["validation"]]
    prior = Counter(labels[item.example_id] for item in splits["development"])
    centroids = _centroids(development, labels)

    def join(predictions: Sequence[PredictionRecord], chooser) -> tuple[JoinedRecord, ...]:
        result = []
        for record in predictions:
            prediction, ranking = chooser(record)
            result.append(JoinedRecord(record.example_id, record.split, labels[record.example_id], prediction, ranking, record.error))
        return tuple(result)

    random_rows = join(validation, lambda record: (_random_label(classes, _stable_unit(seed, record.example_id)), classes))
    prior_rows = join(validation, lambda record: (_prior_label(prior, _stable_unit(seed + 1, record.example_id)), tuple(sorted(prior, key=lambda item: (-prior[item], item)))))
    diagnostic_rows = join(validation, lambda record: _predict_centroid(record, centroids))

    prevalence: dict[str, Any] = {}
    for feature in FEATURES:
        values = [record.features[feature] for record in all_predictions if record.features is not None]
        by_label: dict[str, dict[str, Any]] = {}
        for label in classes:
            label_records = [record for record in all_predictions if labels[record.example_id] == label]
            label_values = [
                record.features[feature] for record in label_records if record.features is not None
            ]
            by_label[label] = {
                "examples": len(label_records),
                "measurement_coverage": (
                    len(label_values) / len(label_records) if label_records else 0.0
                ),
                "mean_value": (
                    sum(label_values) / len(label_values) if label_values else None
                ),
            }
        prevalence[feature] = {
            "measurement_coverage": len(values) / len(all_predictions) if all_predictions else 0.0,
            "mean_value": sum(values) / len(values) if values else None,
            "by_label": by_label,
            "development_mean": (
                sum(record.features[feature] for record in development if record.features is not None)
                / sum(record.features is not None for record in development)
                if any(record.features is not None for record in development)
                else None
            ),
            "validation_mean": (
                sum(record.features[feature] for record in validation if record.features is not None)
                / sum(record.features is not None for record in validation)
                if any(record.features is not None for record in validation)
                else None
            ),
        }
    prevalence["observations"] = {
        observation: {
            "count": sum(observation in record.observations for record in all_predictions),
            "prevalence": sum(observation in record.observations for record in all_predictions) / len(all_predictions),
            "feature": feature,
        }
        for observation, feature in OBSERVATION_FEATURES.items()
    }
    return {
        "dataset": {"version": dataset_version, "examples": len(manifest), "source": "external manifest (read-only)"},
        "split": {"seed": seed, "validation_fraction": validation_fraction, "development": len(splits["development"]), "validation": len(splits["validation"])},
        "inputs": {
            "features": FEATURES,
            "detector": "src.features.road.analyze_road",
            "ground_truth_used_during_extraction": False,
            "label_join_stage": "evaluation_after_prediction_generation",
        },
        "baselines": {
            "random": _metrics(random_rows, classes),
            "class_prior": {**_metrics(prior_rows, classes), "development_distribution": dict(sorted(prior.items()))},
            "road_measurement_centroid": {**_metrics(diagnostic_rows, classes), "feature_source": FEATURES, "training_split": "development"},
        },
        "feature_prevalence_and_coverage": prevalence,
        "limitations": [
            "The road detector measures bottom-region pixel colors; it does not validate road markings.",
            "Centroid distance is a diagnostic feature-only comparison, not production scoring or a promoted geographic claim.",
            "External exploratory data and labels are not copied or modified by this harness.",
            "Manual review and geographic evidence claims remain out of scope.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()
    report = evaluate(load_manifest(args.manifest), validation_fraction=args.validation_fraction, seed=args.seed)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
