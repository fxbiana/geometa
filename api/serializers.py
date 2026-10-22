"""Map ``src.contracts`` dataclasses onto API Pydantic models."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional

from src.contracts import AnalysisResult

from api.schemas import (
    AnalysisResultModel,
    CandidateScoreModel,
    EvidenceModel,
    ImageRegionModel,
    MeasurementModel,
    ObservationModel,
    ScoreContributionModel,
)


def _region(region: Any) -> ImageRegionModel:
    return ImageRegionModel(
        source_id=region.source_id,
        region_type=region.region_type.value
        if hasattr(region.region_type, "value")
        else region.region_type,
        coordinates=region.coordinates,
    )


def analysis_result_to_model(
    result: AnalysisResult,
    *,
    analysis_id: Optional[str] = None,
) -> AnalysisResultModel:
    """Serialize a pipeline AnalysisResult; optionally override analysis_id."""
    effective = result if analysis_id is None else replace(result, analysis_id=analysis_id)
    return AnalysisResultModel(
        analysis_id=effective.analysis_id,
        source_id=effective.source_id,
        source_hash=effective.source_hash,
        status=effective.status.value
        if hasattr(effective.status, "value")
        else effective.status,
        measurements=[
            MeasurementModel(
                id=item.id,
                analysis_id=effective.analysis_id,
                source_id=item.source_id,
                region=_region(item.region),
                feature=item.feature,
                value=item.value,
                unit=item.unit,
                detector_version=item.detector_version,
                schema_version=item.schema_version,
            )
            for item in effective.measurements
        ],
        observations=[
            ObservationModel(
                id=item.id,
                analysis_id=effective.analysis_id,
                source_id=item.source_id,
                region=_region(item.region),
                observation_type=item.observation_type,
                value=item.value,
                confidence=item.confidence,
                state=item.state.value if hasattr(item.state, "value") else item.state,
                supporting_measurement_ids=list(item.supporting_measurement_ids),
                detector_version=item.detector_version,
                schema_version=item.schema_version,
            )
            for item in effective.observations
        ],
        evidence=[
            EvidenceModel(
                id=item.id,
                analysis_id=effective.analysis_id,
                observation_id=item.observation_id,
                value=item.value,
                confidence=item.confidence,
                strength=item.strength,
                reliability=item.reliability,
                diagnosticity=item.diagnosticity,
                geographic_scope=item.geographic_scope,
                direction=item.direction.value
                if hasattr(item.direction, "value")
                else item.direction,
                source_id=item.source_id,
                region=_region(item.region),
                claim_version_id=item.claim_version_id,
                deduplication_key=item.deduplication_key,
            )
            for item in effective.evidence
        ],
        candidates=[
            CandidateScoreModel(
                candidate_id=item.candidate_id,
                candidate_type=item.candidate_type.value
                if hasattr(item.candidate_type, "value")
                else item.candidate_type,
                total=item.total,
                rank=item.rank,
                eligible=item.eligible,
                contributions=[
                    ScoreContributionModel(
                        evidence_id=contribution.evidence_id,
                        candidate_id=contribution.candidate_id,
                        value=contribution.value,
                        direction=contribution.direction.value
                        if hasattr(contribution.direction, "value")
                        else contribution.direction,
                        reason=contribution.reason,
                        calculation_version=contribution.calculation_version,
                    )
                    for contribution in item.contributions
                ],
                inclusion_reason=item.inclusion_reason,
            )
            for item in effective.candidates
        ],
        error=effective.error,
    )
