"""Typed boundaries for the first local-image analysis slice.

These records deliberately keep visual observations separate from geographic
evidence and candidate scores.  They are plain immutable values so callers
cannot accidentally mutate an analysis while it is being explained.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Tuple


class SourceType(str, Enum):
    IMPORTED_IMAGE = "imported_image"


class Availability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class RegionType(str, Enum):
    FULL_IMAGE = "full_image"
    TOP_THIRD = "top_third"
    MIDDLE_THIRD = "middle_third"
    BOTTOM_THIRD = "bottom_third"
    BOUNDING_BOX = "bounding_box"


class ObservationState(str, Enum):
    POSITIVE = "positive"
    AMBIGUOUS = "ambiguous"
    ABSENT = "absent"
    CONFLICTING = "conflicting"


class EvidenceDirection(str, Enum):
    SUPPORTING = "supporting"
    WEAKENING = "weakening"
    INCONCLUSIVE = "inconclusive"
    CONFLICTING = "conflicting"


class CandidateType(str, Enum):
    COUNTRY = "country"


class AnalysisStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True)
class SourceInput:
    """Bytes presented to the prediction pipeline, without ground truth."""

    data: bytes
    name: str = "source"
    source_type: SourceType = SourceType.IMPORTED_IMAGE

    def __post_init__(self) -> None:
        if not self.data:
            raise ValueError("source input must contain image bytes")
        if not self.name:
            raise ValueError("source name must not be empty")


@dataclass(frozen=True)
class SourceValidation:
    valid: bool
    content_hash: str
    availability: Availability
    format: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class ImageRegion:
    source_id: str
    region_type: RegionType
    coordinates: Optional[Tuple[int, int, int, int]] = None


@dataclass(frozen=True)
class Measurement:
    id: str
    analysis_id: str
    source_id: str
    region: ImageRegion
    feature: str
    value: float
    unit: str
    detector_version: str = "prototype-1"
    schema_version: str = "measurement-1"


@dataclass(frozen=True)
class Observation:
    id: str
    analysis_id: str
    source_id: str
    region: ImageRegion
    observation_type: str
    value: Any
    confidence: float
    state: ObservationState
    supporting_measurement_ids: Tuple[str, ...]
    detector_version: str = "prototype-1"
    schema_version: str = "observation-1"

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("observation confidence must be between 0 and 1")


@dataclass(frozen=True)
class Evidence:
    id: str
    analysis_id: str
    observation_id: str
    value: Any
    confidence: float
    strength: float
    reliability: float
    diagnosticity: float
    geographic_scope: str
    direction: EvidenceDirection
    source_id: str
    region: ImageRegion
    claim_version_id: Optional[str] = None
    deduplication_key: Optional[str] = None

    def __post_init__(self) -> None:
        for name in ("confidence", "strength", "reliability", "diagnosticity"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class ScoreContribution:
    evidence_id: str
    candidate_id: str
    value: float
    direction: EvidenceDirection
    reason: str
    calculation_version: str = "score-1"


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    candidate_type: CandidateType
    total: float
    rank: int
    eligible: bool
    contributions: Tuple[ScoreContribution, ...] = field(default_factory=tuple)
    inclusion_reason: str = ""


@dataclass(frozen=True)
class AnalysisResult:
    analysis_id: str
    source_id: str
    source_hash: str
    status: AnalysisStatus
    measurements: Tuple[Measurement, ...] = field(default_factory=tuple)
    observations: Tuple[Observation, ...] = field(default_factory=tuple)
    evidence: Tuple[Evidence, ...] = field(default_factory=tuple)
    candidates: Tuple[CandidateScore, ...] = field(default_factory=tuple)
    error: Optional[str] = None


@dataclass(frozen=True)
class ExplanationInput:
    analysis: AnalysisResult


@dataclass(frozen=True)
class ExplanationOutput:
    analysis_id: str
    status: AnalysisStatus
    summary: str
    candidates: Tuple[CandidateScore, ...] = field(default_factory=tuple)
    evidence: Tuple[Evidence, ...] = field(default_factory=tuple)
