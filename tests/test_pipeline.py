import ast
import inspect
from io import BytesIO
from pathlib import Path

from PIL import Image

from src.claims import CLAIM_CATALOG_VERSION
from src.contracts import AnalysisStatus, SourceInput
from src.pipeline import analyze_source, run_analysis
from src.source import source_hash


def image_bytes(color=(100, 100, 100), size=(6, 6)):
    image = Image.new("RGB", size, color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def yellow_road_bytes(size=(12, 12)):
    """Bottom-third yellow pixels trigger possible_yellow_marking."""
    image = Image.new("RGB", size, (40, 40, 40))
    for y in range(2 * size[1] // 3, size[1]):
        for x in range(size[0]):
            image.putpixel((x, y), (200, 180, 50))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_run_analysis_no_claims_is_insufficient_evidence():
    """Gray surface claim has empty supports → no evidence → abstain."""
    data = image_bytes()
    result = run_analysis(data)
    assert result.source_hash == source_hash(data)
    assert result.measurements
    assert result.observations
    assert result.evidence == ()
    assert result.candidates == ()
    assert result.status is AnalysisStatus.INSUFFICIENT_EVIDENCE


def test_run_analysis_unknown_catalog_is_insufficient():
    result = run_analysis(yellow_road_bytes(), claim_version="claims-does-not-exist")
    assert result.status is AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == ()
    assert result.candidates == ()


def test_run_analysis_matching_claim_ranks_candidates():
    result = run_analysis(yellow_road_bytes(), claim_version=CLAIM_CATALOG_VERSION)
    assert result.status is AnalysisStatus.COMPLETED
    assert result.evidence
    assert result.candidates
    assert {c.candidate_id for c in result.candidates} == {"US", "CA"}
    assert all(c.eligible for c in result.candidates)
    assert all(c.contributions for c in result.candidates)
    assert result.candidates[0].rank == 1
    assert any(
        item.claim_version_id == "claim:road:yellow_center_line:v1"
        for item in result.evidence
    )


def test_run_analysis_accepts_path(tmp_path: Path):
    path = tmp_path / "road.png"
    path.write_bytes(image_bytes())
    result = run_analysis(path)
    assert result.status is AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.source_id == "road.png"


def test_analyze_source_invalid_bytes_fails_without_crash():
    result = analyze_source(SourceInput(b"not-an-image", "bad.bin"))
    assert result.status is AnalysisStatus.FAILED
    assert result.error
    assert result.measurements == ()
    assert result.observations == ()
    assert result.evidence == ()


def test_pipeline_modules_never_import_ground_truth():
    """Prediction path must not import dataset / label loaders."""
    root = Path(__file__).resolve().parents[1] / "src"
    forbidden = {"dataset", "annotations", "evaluation_harness"}
    for module_name in ("pipeline.py", "evidence.py", "claims.py", "knowledge.py"):
        tree = ast.parse((root / module_name).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
                if node.module.startswith("."):
                    imported.update(
                        alias.name.split(".")[0] for alias in node.names if alias.name
                    )
        assert not (imported & forbidden), f"{module_name} imports {imported & forbidden}"


def test_run_analysis_signature_rejects_ground_truth_params():
    params = set(inspect.signature(run_analysis).parameters)
    assert "label" not in params
    assert "labels" not in params
    assert "ground_truth" not in params
    assert "actual_location" not in params
    assert "country" not in params
