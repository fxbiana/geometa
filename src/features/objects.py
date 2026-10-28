"""Open-vocabulary visual object detector (YOLO-World).

Returns only visual ``Observation`` / ``Measurement`` records.  Claim matching
and place inference live elsewhere and must not be done here.

Graceful degrade: if ultralytics is missing, weights cannot load, or inference
fails, this module returns empty observations instead of raising into the API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Tuple

from PIL import Image

try:  # Support both ``python -m src.main`` and package imports.
    from ..contracts import (
        ImageRegion,
        Measurement,
        Observation,
        ObservationState,
        RegionType,
    )
except ImportError:  # pragma: no cover - compatibility for old scripts
    from contracts import ImageRegion, Measurement, Observation, ObservationState, RegionType

logger = logging.getLogger(__name__)

DETECTOR_VERSION = "yolo-world-v1"
DEFAULT_MODEL_NAME = "yolov8s-world.pt"

# Prompt labels passed to YOLO-World (open vocabulary).
OBJECT_CLASS_LABELS: Tuple[str, ...] = (
    "bollard",
    "guardrail",
    "road marking",
    "sign",
    "pole",
)

# Stable snake_case observation types for later claims matching.
OBSERVATION_TYPE_BY_LABEL = {
    "bollard": "object_bollard",
    "guardrail": "object_guardrail",
    "road marking": "object_road_marking",
    "sign": "object_sign",
    "pole": "object_pole",
}


@dataclass(frozen=True)
class ObjectAnalysis:
    measurements: Tuple[Measurement, ...]
    observations: Tuple[Observation, ...]


# Lazily cached model handle; None means "not attempted", False means "unavailable".
_model_cache: Any = None
_model_load_failed: bool = False


def _observation_type_for_label(label: str) -> str:
    key = label.strip().lower()
    if key in OBSERVATION_TYPE_BY_LABEL:
        return OBSERVATION_TYPE_BY_LABEL[key]
    # Fallback keeps snake_case stability for unexpected synonyms.
    return "object_" + key.replace(" ", "_").replace("-", "_")


def _load_yolo_world(model_name: str = DEFAULT_MODEL_NAME) -> Any:
    """Load YOLO-World and set the street-furniture class prompts.

    Returns ``None`` when the dependency or weights are unavailable.
    """
    global _model_cache, _model_load_failed
    if _model_load_failed:
        return None
    if _model_cache is not None:
        return _model_cache
    try:
        from ultralytics import YOLOWorld  # type: ignore
    except ImportError:
        logger.info("ultralytics not installed; object detector returns no observations")
        _model_load_failed = True
        return None
    try:
        model = YOLOWorld(model_name)
        model.set_classes(list(OBJECT_CLASS_LABELS))
    except Exception as exc:  # pragma: no cover - depends on network/weights
        logger.warning("YOLO-World weights unavailable (%s); returning no observations", exc)
        _model_load_failed = True
        return None
    _model_cache = model
    return model


def reset_model_cache() -> None:
    """Clear the cached model (used by tests)."""
    global _model_cache, _model_load_failed
    _model_cache = None
    _model_load_failed = False


def _boxes_from_ultralytics_result(result: Any) -> List[Tuple[str, float, Tuple[int, int, int, int]]]:
    """Normalize one ultralytics result into (label, confidence, xyxy) tuples."""
    detections: List[Tuple[str, float, Tuple[int, int, int, int]]] = []
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return detections
    names = getattr(result, "names", None) or {}
    xyxy = boxes.xyxy
    confs = boxes.conf
    clss = boxes.cls
    # Tensor-like or plain sequences.
    for i in range(len(boxes)):
        try:
            x1, y1, x2, y2 = (int(round(float(v))) for v in xyxy[i].tolist())
            conf = float(confs[i].item() if hasattr(confs[i], "item") else confs[i])
            cls_idx = int(clss[i].item() if hasattr(clss[i], "item") else clss[i])
        except Exception:
            continue
        if isinstance(names, dict):
            label = str(names.get(cls_idx, OBJECT_CLASS_LABELS[cls_idx] if cls_idx < len(OBJECT_CLASS_LABELS) else cls_idx))
        else:
            label = str(names[cls_idx] if cls_idx < len(names) else cls_idx)
        detections.append((label, conf, (x1, y1, x2, y2)))
    return detections


def _default_infer(
    image: Image.Image,
    *,
    model_name: str,
    confidence_threshold: float,
) -> List[Tuple[str, float, Tuple[int, int, int, int]]]:
    model = _load_yolo_world(model_name)
    if model is None:
        return []
    try:
        results = model.predict(image, conf=confidence_threshold, verbose=False)
    except Exception as exc:  # pragma: no cover - runtime/device failures
        logger.warning("YOLO-World inference failed (%s); returning no observations", exc)
        return []
    if not results:
        return []
    return _boxes_from_ultralytics_result(results[0])


def detect_objects(
    image: Image.Image,
    *,
    source_id: str = "source",
    analysis_id: str = "analysis",
    detector_version: str = DETECTOR_VERSION,
    model_name: str = DEFAULT_MODEL_NAME,
    confidence_threshold: float = 0.1,
    infer_fn: Optional[
        Callable[..., List[Tuple[str, float, Tuple[int, int, int, int]]]]
    ] = None,
) -> ObjectAnalysis:
    """Detect prompted street-furniture classes and emit visual observations.

    ``infer_fn``, when provided, replaces the YOLO-World call (for unit tests).
    It must return a list of ``(label, confidence, (x1, y1, x2, y2))``.
    """
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("image must have positive dimensions")

    runner = infer_fn if infer_fn is not None else _default_infer
    try:
        raw = runner(
            image,
            model_name=model_name,
            confidence_threshold=confidence_threshold,
        )
    except TypeError:
        # Allow simple mocks that only accept the image.
        raw = runner(image)  # type: ignore[call-arg]
    except Exception as exc:
        logger.warning("object infer_fn failed (%s); returning no observations", exc)
        raw = []

    observations: List[Observation] = []
    measurements: List[Measurement] = []

    for index, (label, confidence, box) in enumerate(raw):
        conf = max(0.0, min(1.0, float(confidence)))
        if conf < confidence_threshold:
            continue
        x1, y1, x2, y2 = box
        # Clamp to image bounds; skip degenerate boxes.
        x1 = max(0, min(width - 1, int(x1)))
        y1 = max(0, min(height - 1, int(y1)))
        x2 = max(0, min(width, int(x2)))
        y2 = max(0, min(height, int(y2)))
        if x2 <= x1 or y2 <= y1:
            continue

        observation_type = _observation_type_for_label(label)
        region = ImageRegion(source_id, RegionType.BOUNDING_BOX, (x1, y1, x2, y2))
        measurement_id = f"{analysis_id}:measurement:object_conf:{index}"
        measurements.append(
            Measurement(
                id=measurement_id,
                analysis_id=analysis_id,
                source_id=source_id,
                region=region,
                feature=f"object_confidence:{observation_type}",
                value=conf,
                unit="ratio_0_1",
                detector_version=detector_version,
            )
        )
        observations.append(
            Observation(
                id=f"{analysis_id}:observation:{observation_type}:{index}",
                analysis_id=analysis_id,
                source_id=source_id,
                region=region,
                observation_type=observation_type,
                value=True,
                confidence=conf,
                state=ObservationState.POSITIVE,
                supporting_measurement_ids=(measurement_id,),
                detector_version=detector_version,
            )
        )

    return ObjectAnalysis(tuple(measurements), tuple(observations))


def _cli(argv: Optional[Sequence[str]] = None) -> int:
    """Load one image path and print object observations (real-run smoke path)."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="GeoMeta YOLO-World object detector smoke run")
    parser.add_argument(
        "image_path",
        help="Path to a street-view still (PNG/JPEG). Example: images/<fixture>.png",
    )
    parser.add_argument("--conf", type=float, default=0.1, help="Confidence threshold")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Ultralytics YOLO-World weights name")
    args = parser.parse_args(list(argv) if argv is not None else None)

    with Image.open(args.image_path) as image:
        image.load()
        rgb = image.convert("RGB")
        result = detect_objects(
            rgb,
            source_id=args.image_path,
            analysis_id="smoke",
            model_name=args.model,
            confidence_threshold=args.conf,
        )

    payload = [
        {
            "observation_type": obs.observation_type,
            "confidence": obs.confidence,
            "region_type": obs.region.region_type.value,
            "coordinates": obs.region.coordinates,
        }
        for obs in result.observations
    ]
    print(json.dumps({"count": len(payload), "observations": payload}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
