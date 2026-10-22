# GeoMeta API

FastAPI skeleton that exposes the local-image analysis pipeline over HTTP.
Frontend (Next.js + Clerk) will call these routes later; the analysis path stays in Python.

## Setup

From the repository root:

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Open interactive docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Routes

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/health` | Liveness |
| `POST` | `/v1/analyses` | Upload `file` **or** form field `path` → source validation + road analysis |
| `GET` | `/v1/analyses/{analysis_id}` | In-memory lookup |
| `POST` | `/v1/practice/start` | Stub practice prompt |
| `POST` | `/v1/practice/{session_id}/attempt` | Stub guess recording |
| `GET` | `/v1/progress` | Stub empty mastery |
| `GET` | `/v1/metas` | Learnable topics from `META_CATEGORIES` |

### Create an analysis

Multipart form — upload:

```bash
curl -X POST http://127.0.0.1:8000/v1/analyses -F "file=@some.png"
```

Or a local path reference:

```bash
curl -X POST http://127.0.0.1:8000/v1/analyses -F "path=C:/path/to/image.png"
```

Until production geographic claims are wired, a valid image typically returns
`status: "insufficient_evidence"` with measurements/observations filled and
empty `evidence` / `candidates`. That is intentional — the API does not invent
country predictions.

## Tests

`httpx` is required by FastAPI's `TestClient` (install if missing: `pip install httpx`).

```bash
python -m pytest tests/test_api_health.py tests/test_api_analyses.py -q
```

## Auth

Clerk JWT verification is not implemented. See the TODO comment in `api/main.py`.
