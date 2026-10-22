"""Local-image analysis orchestrator: source → road → evidence → score → explain.

Status semantics
----------------
* ``FAILED`` — source validation or image decode failed.
* ``INSUFFICIENT_EVIDENCE`` — measurements/observations exist but no
  claim-backed geographic evidence qualifies a candidate.
* ``COMPLETED`` — at least one eligible country candidate from claim-backed
  evidence.

Ground-truth labels are never accepted or read by this module.
"""

from io import BytesIO
from pathlib import Path
from typing import Union

from PIL import Image

from .claims import CLAIM_CATALOG_VERSION
from .contracts import (
    AnalysisResult,
    AnalysisStatus,
    ExplanationInput,
    SourceInput,
)
from .evidence import build_evidence, rank_candidates
from .features.road import analyze_road
from .reasoning import explain
from .source import load_source, validate_source


def run_analysis(
    source_bytes_or_path: Union[bytes, str, Path, SourceInput],
    *,
    claim_version: str = CLAIM_CATALOG_VERSION,
) -> AnalysisResult:
    """Run the full local-image vertical slice and return an AnalysisResult.

    Accepts raw image bytes, a filesystem path, or a ``SourceInput``.  Does not
    accept or consult ground-truth labels.
    """
    source = _coerce_source(source_bytes_or_path)
    return analyze_source(source, claim_version=claim_version)


def analyze_source(
    source: SourceInput,
    *,
    claim_version: str = CLAIM_CATALOG_VERSION,
) -> AnalysisResult:
    """Validate a source, run road analysis, build evidence, and score."""
    validation = validate_source(source)
    source_id = source.name
    analysis_id = f"analysis:{validation.content_hash[:16]}"

    if not validation.valid:
        return AnalysisResult(
            analysis_id=analysis_id,
            source_id=source_id,
            source_hash=validation.content_hash,
            status=AnalysisStatus.FAILED,
            error=validation.error or "invalid source",
        )

    try:
        with Image.open(BytesIO(source.data)) as image:
            image.load()
            road = analyze_road(
                image,
                source_id=source_id,
                analysis_id=analysis_id,
            )
    except (OSError, ValueError) as exc:
        return AnalysisResult(
            analysis_id=analysis_id,
            source_id=source_id,
            source_hash=validation.content_hash,
            status=AnalysisStatus.FAILED,
            error=f"image decode/analysis failed: {exc}",
        )

    evidence = build_evidence(road.observations, claim_version)
    candidates = rank_candidates(evidence) if evidence else ()
    eligible = tuple(c for c in candidates if c.eligible)

    if eligible:
        status = AnalysisStatus.COMPLETED
    else:
        status = AnalysisStatus.INSUFFICIENT_EVIDENCE

    result = AnalysisResult(
        analysis_id=analysis_id,
        source_id=source_id,
        source_hash=validation.content_hash,
        status=status,
        measurements=road.measurements,
        observations=road.observations,
        evidence=evidence,
        candidates=candidates,
    )
    # Explanation is derived from the stored result; never invents evidence.
    explain(ExplanationInput(result))
    return result


def _coerce_source(
    source_bytes_or_path: Union[bytes, str, Path, SourceInput],
) -> SourceInput:
    if isinstance(source_bytes_or_path, SourceInput):
        return source_bytes_or_path
    if isinstance(source_bytes_or_path, (str, Path)):
        source, _ = load_source(source_bytes_or_path)
        return source
    if isinstance(source_bytes_or_path, bytes):
        return SourceInput(source_bytes_or_path, name="source")
    raise TypeError(
        "run_analysis expects bytes, a path, or SourceInput; "
        f"got {type(source_bytes_or_path).__name__}"
    )
