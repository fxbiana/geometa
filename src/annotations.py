"""M1-FE2 manual visual-annotation contract and validation helpers.

Country labels are evaluation metadata and are deliberately excluded from this
record and payload API. The contract represents uncertainty explicitly instead
of converting an unobservable feature into absence. This module validates
annotation records only; it is not part of prediction extraction.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple


class Presence(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    NOT_DETERMINABLE = "not_determinable"
    CONFLICTING = "conflicting"


class Visibility(str, Enum):
    """How much of the feature can be inspected, including why it cannot."""

    CLEARLY_VISIBLE = "clearly_visible"
    VISIBLE = "visible"  # compatibility spelling for clearly visible
    PARTIALLY_VISIBLE = "partially_visible"
    PARTIAL = "partial"  # compatibility spelling
    OBSCURED = "obscured"
    OUTSIDE_FRAME = "outside_frame"
    TOO_LOW_QUALITY = "too_low_quality"
    CONTAMINATED = "contaminated"
    UNCERTAIN = "uncertain"
    NOT_VISIBLE = "not_visible"
    UNKNOWN = "unknown"


class ImageQuality(str, Enum):
    UNKNOWN = "unknown"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class InterfaceContamination(str, Enum):
    UNKNOWN = "unknown"
    NONE = "none"
    POSSIBLE = "possible"
    CLEAR = "clear"


class FeatureFamily(str, Enum):
    ROAD = "road"
    VEGETATION = "vegetation"
    SIGNS = "signs"
    BUILT_ENVIRONMENT = "built_environment"
    UTILITIES = "utilities"
    TERRAIN = "terrain"
    VEHICLES_CAPTURE_CONTEXT = "vehicles_capture_context"


# These remain separate visual observations rather than being folded into a
# generic road feature.
ROAD_MARKING_FEATURES = frozenset(("road_marking", "raised_marker"))


@dataclass(frozen=True)
class Interpretation:
    """One competing reading of a visual feature."""

    value: str
    confidence: Optional[float] = None
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("interpretation value must not be empty")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("interpretation confidence must be between 0 and 1")


@dataclass(frozen=True)
class VisualAnnotation:
    feature_family: FeatureFamily
    feature: str
    presence: Presence
    visibility: Visibility
    confidence: Optional[float] = None
    interpretations: Tuple[Interpretation, ...] = field(default_factory=tuple)
    region: Optional[str] = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.feature.strip():
            raise ValueError("visual annotation feature must not be empty")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("annotation confidence must be between 0 and 1")
        if self.visibility in (
            Visibility.OBSCURED,
            Visibility.OUTSIDE_FRAME,
            Visibility.TOO_LOW_QUALITY,
            Visibility.CONTAMINATED,
            Visibility.UNCERTAIN,
            Visibility.NOT_VISIBLE,
            Visibility.UNKNOWN,
        ) and self.presence not in (
            Presence.UNKNOWN,
            Presence.NOT_DETERMINABLE,
        ):
            raise ValueError(
                "unobservable feature visibility must have an unknown or "
                "not_determinable state"
            )
        if len(self.interpretations) > 1 and any(
            item.confidence is None for item in self.interpretations
        ):
            raise ValueError("competing interpretations require confidence values")


@dataclass(frozen=True)
class AnnotatorMetadata:
    annotator_id: str
    annotated_at: str
    tool_version: str = "m1-fe2-manual-1"

    def __post_init__(self) -> None:
        if not self.annotator_id.strip() or not self.annotated_at.strip():
            raise ValueError("annotator_id and annotated_at are required")


@dataclass(frozen=True)
class AnnotationRecord:
    annotation_id: str
    image_id: str
    image_path: str
    content_hash: str
    annotator: Optional[AnnotatorMetadata]
    image_quality: ImageQuality
    interface_contamination: InterfaceContamination
    visual_annotations: Tuple[VisualAnnotation, ...] = field(default_factory=tuple)
    review_status: str = "needs_review"
    schema_version: str = "m1-fe2-2"

    def __post_init__(self) -> None:
        if not self.annotation_id.strip() or not self.image_id.strip() or not self.image_path.strip():
            raise ValueError("annotation and image identities and path are required")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.content_hash):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        if self.review_status not in ("needs_review", "annotated", "reviewed", "frozen"):
            raise ValueError("invalid annotation review_status")
        if self.review_status == "needs_review" and self.annotator is not None:
            raise ValueError("needs_review records must not claim an annotator")
        if self.review_status != "needs_review" and self.annotator is None:
            raise ValueError("annotator metadata is required after annotation")

    def to_dict(self) -> Dict[str, Any]:
        return _json_ready(asdict(self))


class AnnotationValidationError(ValueError):
    """Raised when a payload cannot be represented by the annotation contract."""


def validate_annotation_payload(payload: Mapping[str, Any]) -> AnnotationRecord:
    """Parse and validate a JSON-compatible annotation object."""
    if not isinstance(payload, Mapping):
        raise AnnotationValidationError("annotation must be an object")
    try:
        visual = []
        for item in payload.get("visual_annotations", []):
            interpretations = tuple(
                Interpretation(
                    value=entry["value"],
                    confidence=entry.get("confidence"),
                    rationale=entry.get("rationale", ""),
                )
                for entry in item.get("interpretations", [])
            )
            visual.append(
                VisualAnnotation(
                    feature_family=FeatureFamily(item["feature_family"]),
                    feature=item["feature"],
                    presence=Presence(item["presence"]),
                    visibility=Visibility(item["visibility"]),
                    confidence=item.get("confidence"),
                    interpretations=interpretations,
                    region=item.get("region"),
                    note=item.get("note", ""),
                )
            )
        if "country_label" in payload:
            raise AnnotationValidationError(
                "country_label is evaluation metadata and is not accepted by annotation validation"
            )
        metadata = payload.get("annotator")
        annotator = (
            AnnotatorMetadata(
                metadata["annotator_id"],
                metadata["annotated_at"],
                metadata.get("tool_version", "m1-fe2-manual-1"),
            )
            if metadata is not None
            else None
        )
        return AnnotationRecord(
            annotation_id=payload["annotation_id"],
            image_id=payload["image_id"],
            image_path=payload["image_path"],
            content_hash=payload["content_hash"],
            annotator=annotator,
            image_quality=ImageQuality(payload.get("image_quality", "unknown")),
            interface_contamination=InterfaceContamination(
                payload.get("interface_contamination", "unknown")
            ),
            visual_annotations=tuple(visual),
            review_status=payload.get("review_status", "needs_review"),
            schema_version=payload.get("schema_version", "m1-fe2-3"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AnnotationValidationError(str(exc)) from exc


def load_annotations(path: str) -> Tuple[AnnotationRecord, ...]:
    """Load JSONL annotation records; no prediction or detector code is called."""
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                records.append(validate_annotation_payload(json.loads(line)))
            except (json.JSONDecodeError, AnnotationValidationError) as exc:
                raise AnnotationValidationError(
                    "line {0}: {1}".format(line_number, exc)
                ) from exc
    if not records:
        raise AnnotationValidationError("annotation JSONL contains no records")
    ids = [record.annotation_id for record in records]
    if len(ids) != len(set(ids)):
        raise AnnotationValidationError("annotation IDs must be unique")
    image_ids = [record.image_id for record in records]
    if len(image_ids) != len(set(image_ids)):
        raise AnnotationValidationError("annotation image IDs must be unique")
    return tuple(records)


def write_annotations(path: str, records: Tuple[AnnotationRecord, ...]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")


def freeze_annotations(records: Tuple[AnnotationRecord, ...]) -> Tuple[AnnotationRecord, ...]:
    """Return frozen records only after every record has human review metadata."""
    if any(record.review_status != "reviewed" for record in records):
        raise AnnotationValidationError(
            "cannot freeze annotations while records need annotation or review"
        )
    return tuple(
        AnnotationRecord(
            annotation_id=record.annotation_id,
            image_id=record.image_id,
            image_path=record.image_path,
            content_hash=record.content_hash,
            annotator=record.annotator,
            image_quality=record.image_quality,
            interface_contamination=record.interface_contamination,
            visual_annotations=record.visual_annotations,
            review_status="frozen",
            schema_version=record.schema_version,
        )
        for record in records
    )


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value
