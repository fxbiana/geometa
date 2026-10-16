# geometa
fun geoguessr project using plonkit!
https://www.plonkit.net/guide

## Exploratory feature evaluation

The read-only M1-FE harness accepts an external CSV, JSON, or JSONL manifest.
Each row must provide an image path (`image_path`, `path`, or `filename`) and
country label (`country`, `label`, or `target`). Paths are resolved relative
to the manifest. It does not copy or modify the historical dataset:

```powershell
.venv\Scripts\python.exe -m src.evaluation_harness path\to\manifest.csv `
  --output evaluation-report.json
```

The report uses a stable, stratified provisional split, deterministic random
and class-prior baselines, and a diagnostic nearest-development-centroid
comparison over the existing road measurements. Labels are joined only after
feature extraction. The centroid comparison is not production scoring and
does not promote raw pixel measurements to geographic evidence.
