from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from api.main import app
from api.store import analysis_store

client = TestClient(app)


def _tiny_png_bytes(color=(100, 100, 100), size=(6, 6)) -> bytes:
    image = Image.new("RGB", size, color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_create_analysis_from_upload_returns_measurements():
    data = _tiny_png_bytes()
    response = client.post(
        "/v1/analyses",
        files={"file": ("fixture.png", data, "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_evidence"
    assert body["source_hash"]
    assert body["measurements"]
    assert body["observations"]
    assert body["evidence"] == []
    assert body["candidates"] == []
    assert analysis_store.get(body["analysis_id"]) is not None


def test_get_analysis_by_id():
    data = _tiny_png_bytes()
    created = client.post(
        "/v1/analyses",
        files={"file": ("fixture.png", data, "image/png")},
    ).json()
    response = client.get(f"/v1/analyses/{created['analysis_id']}")
    assert response.status_code == 200
    assert response.json()["analysis_id"] == created["analysis_id"]


def test_get_analysis_missing_is_404():
    response = client.get("/v1/analyses/does-not-exist")
    assert response.status_code == 404


def test_create_analysis_requires_file_or_path():
    response = client.post("/v1/analyses")
    assert response.status_code == 400
