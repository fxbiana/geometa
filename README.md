# geometa
fun geoguessr project using plonkit!
https://www.plonkit.net/guide

## Frontend (`web/`)

The product UI scaffolds under [`web/`](web/) as a Next.js App Router (TypeScript) app — learnable interactive metas for GeoGuessr-style practice. It needs **Node 20.9+** to install and run; Clerk auth is not wired yet. Python under `src/` remains the analysis/research core for now. See [`web/README.md`](web/README.md).

Product API shape (learn + practice + analyze): [`docs/api/openapi.yaml`](docs/api/openapi.yaml). Local Postgres: [`db/README.md`](db/README.md). Analysis entrypoint: `src.pipeline.analyze_source`.

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

## M1-FE2 pilot annotations

`data/m1_fe2_pilot_manifest.json` is a deterministic 100-image metadata
manifest. It references the approved external subset by relative path and
content hash; no external images are copied or modified. The ignored dataset
must be available at `images/compressed_dataset` (or pass another root to the
generator). Recreate it from the approved subset manifest with:

```powershell
.venv\Scripts\python.exe tools\generate_m1_fe2_pilot.py `
  path\to\approved-external-dataset-subset-manifest.json `
  data\m1_fe2_pilot_manifest.json
```

Manual records use `src.annotations`: country labels remain separate from
visual annotations, and presence, visibility, competing interpretations,
quality, interface contamination, annotator metadata, and SHA-256 hashes are
validated without turning “not visible” into “absent”. Visibility preserves
causes such as `outside_frame`, `obscured`, `too_low_quality`, and
`contaminated`; these require `unknown` or `not_determinable` presence.

### Human annotation workflow (schema `m1-fe2-3`)

`data/m1_fe2_pilot_annotations.jsonl` is the version-controlled, 100-record
template. Every record starts as `needs_review`, has no annotator identity,
contains no country-label field, and has empty visual annotations. The
country-bearing pilot manifest remains evaluation metadata; it is not copied
into annotation records. The external image corpus remains ignored.

Generate or validate records without invoking detector extraction:

```powershell
.venv\Scripts\python.exe tools\manage_m1_fe2_annotations.py generate `
  data\m1_fe2_pilot_manifest.json data\m1_fe2_pilot_annotations.jsonl
.venv\Scripts\python.exe tools\manage_m1_fe2_annotations.py validate `
  data\m1_fe2_pilot_annotations.jsonl
```

For each image, a human reviewer must inspect the referenced image, choose
visual feature records (including presence, visibility cause, uncertainty, and
competing interpretations), record image quality/interface contamination,
enter an annotator ID and timestamp, and change `review_status` to
`reviewed`. A second reviewer should check the record before freezing. The
freeze command exists but must not be run until that interaction is complete:

```powershell
.venv\Scripts\python.exe tools\manage_m1_fe2_annotations.py freeze `
  data\m1_fe2_pilot_annotations.jsonl data\m1_fe2_pilot_annotations.frozen.jsonl
```

Detector outputs and country labels are joined only in a later, separately
approved evaluation; this workflow does not run or promote detector accuracy.

Visual annotations use one of these descriptive feature families:
`road`, `vegetation`, `signs`, `built_environment`, `utilities`, `terrain`,
or `vehicles_capture_context`. Each observation retains presence, explicit
visibility cause, confidence/uncertainty, and optional competing
interpretations. `road_marking` and `raised_marker` remain separate road
features; they must not be collapsed into a generic road observation.
Existing empty `needs_review` records remain valid; records with observations
must use the `feature_family` field under schema `m1-fe2-3`. No feature labels
are prefilled by template generation.
