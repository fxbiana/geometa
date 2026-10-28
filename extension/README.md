# GeoMeta unpacked extension

Load this folder in Chrome to see whether the local analysis API is running and which countries the current claims support.

1. Start the API from the repository root:

```bash
.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

2. Open `chrome://extensions`.
3. Turn on **Developer mode**.
4. Choose **Load unpacked** and select this `extension/` directory (the folder that contains `manifest.json`).

The popup can check `GET /health`, analyze the visible tab, or analyze an image file. It posts the image to `POST /v1/analyses` and lists:

- the status (`completed` or `insufficient_evidence`)
- the metas whose observations matched an approved claim
- the countries those claims support, with the claim score and that score’s share of the positive total

Score share is a display of the heuristic score. It is not a calibrated probability. The extension does not click, type, or submit anything on GeoGuessr.
