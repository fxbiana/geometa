"""Pydantic request/response models aligned with ``src.contracts`` vocabulary."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


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


class ImageRegionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    region_type: RegionType
    coordinates: Optional[Tuple[int, int, int, int]] = None


class MeasurementModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    analysis_id: str
    source_id: str
    region: ImageRegionModel
    feature: str
    value: float
    unit: str
    detector_version: str = "prototype-1"
    schema_version: str = "measurement-1"


class ObservationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    analysis_id: str
    source_id: str
    region: ImageRegionModel
    observation_type: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    state: ObservationState
    supporting_measurement_ids: List[str]
    detector_version: str = "prototype-1"
    schema_version: str = "observation-1"


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    analysis_id: str
    observation_id: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    strength: float = Field(ge=0, le=1)
    reliability: float = Field(ge=0, le=1)
    diagnosticity: float = Field(ge=0, le=1)
    geographic_scope: str
    direction: EvidenceDirection
    source_id: str
    region: ImageRegionModel
    claim_version_id: Optional[str] = None
    deduplication_key: Optional[str] = None


class ScoreContributionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    candidate_id: str
    value: float
    direction: EvidenceDirection
    reason: str
    calculation_version: str = "score-1"


class CandidateScoreModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    candidate_type: CandidateType
    total: float
    rank: int
    eligible: bool
    contributions: List[ScoreContributionModel] = Field(default_factory=list)
    inclusion_reason: str = ""


class AnalysisResultModel(BaseModel):
    """AnalysisResult-shaped JSON returned by the analyses API."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    source_id: str
    source_hash: str
    status: AnalysisStatus
    measurements: List[MeasurementModel] = Field(default_factory=list)
    observations: List[ObservationModel] = Field(default_factory=list)
    evidence: List[EvidenceModel] = Field(default_factory=list)
    candidates: List[CandidateScoreModel] = Field(default_factory=list)
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "geometa-api"
    version: str


class PracticeStartResponse(BaseModel):
    """Stub practice-session payload (not backed by the analysis pipeline)."""

    session_id: str
    prompt_id: str
    prompt_text: str
    feature_focus: str
    disclosure_level: str = "hint"


class PracticeAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guessed_country: str
    guessed_region: Optional[str] = None
    notes: Optional[str] = None


class PracticeAttemptResponse(BaseModel):
    session_id: str
    attempt_id: str
    guessed_country: str
    guessed_region: Optional[str] = None
    recorded: bool = True
    explanation_summary: str
    status: AnalysisStatus = AnalysisStatus.INSUFFICIENT_EVIDENCE


class ProgressResponse(BaseModel):
    """Stub mastery summary — empty until study evaluation is wired."""

    mastery_by_category: Dict[str, float] = Field(default_factory=dict)
    rounds_completed: int = 0
    sample_insufficient: bool = True


class MetaTopic(BaseModel):
    id: str
    category: str
    title: str
    description: str


class MetasListResponse(BaseModel):
    topics: List[MetaTopic]
