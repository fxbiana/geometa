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


def _yellow_road_bytes(size=(12, 12)) -> bytes:
    image = Image.new("RGB", size, (40, 40, 40))
    for y in range(2 * size[1] // 3, size[1]):
        for x in range(size[0]):
            image.putpixel((x, y), (200, 180, 50))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_yellow_road_upload_returns_claim_countries_and_score():
    response = client.post(
        "/v1/analyses",
        files={"file": ("yellow.png", _yellow_road_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert any(
        item["observation_type"] == "possible_yellow_marking" for item in body["observations"]
    )
    assert any(
        item["claim_version_id"] == "claim:road:yellow_center_line:v1" for item in body["evidence"]
    )
    assert {item["candidate_id"] for item in body["candidates"]} == {"US", "CA"}
    assert [item["rank"] for item in body["candidates"]] == [1, 2]
    assert all(item["eligible"] for item in body["candidates"])
    assert all(item["total"] > 0 for item in body["candidates"])


def test_extension_origin_can_call_analyses():
    origin = "chrome-extension://dnhpgpdjomkidkkgbomiphajbpnpfdgb"
    response = client.post(
        "/v1/analyses",
        files={"file": ("fixture.png", _tiny_png_bytes(), "image/png")},
        headers={"Origin": origin},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.json()["status"] == "insufficient_evidence"
