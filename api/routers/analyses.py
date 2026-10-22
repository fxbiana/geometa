"""Analysis endpoints: real source validation + road measurements/observations.

Geographic evidence and country candidates are not invented.  Until production
claim mapping is wired, successful road analysis returns
``insufficient_evidence`` with empty ``evidence`` / ``candidates``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from src.contracts import SourceInput
from src.pipeline import analyze_source
from src.source import load_source

from api.serializers import analysis_result_to_model
from api.schemas import AnalysisResultModel
from api.store import analysis_store

router = APIRouter(prefix="/v1/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisResultModel)
async def create_analysis(
    file: Optional[UploadFile] = File(None),
    path: Optional[str] = Form(None),
) -> AnalysisResultModel:
    """Accept an uploaded image or a local path reference and run analysis.

    Never joins country labels into the prediction path.  Does not invent
    geographic evidence when claim mapping is unavailable.
    """
    if file is None and not path:
        raise HTTPException(
            status_code=400,
            detail="Provide either an image upload (file) or a local path reference (path).",
        )
    if file is not None and path:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of file or path, not both.",
        )

    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        name = file.filename or "upload.bin"
        source = SourceInput(data=data, name=name)
    else:
        assert path is not None
        resolved = Path(path)
        if not resolved.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a readable file: {path}")
        try:
            source, _validation = load_source(resolved)
        except OSError as exc:
            raise HTTPException(status_code=400, detail=f"Unable to read path: {exc}") from exc

    pipeline_result = analyze_source(source)
    # Mint a unique API analysis id so retries never overwrite prior attempts.
    api_result = analysis_result_to_model(pipeline_result, analysis_id=str(uuid4()))
    return analysis_store.put(api_result)


@router.get("/{analysis_id}", response_model=AnalysisResultModel)
def get_analysis(analysis_id: str) -> AnalysisResultModel:
    result = analysis_store.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result
