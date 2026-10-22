# geometa MVP API

Contract-first OpenAPI 3.1 surface for the product. Spec only — no server yet.

## Spec

- [`openapi.yaml`](./openapi.yaml) — paths, auth, and schemas aligned with `src/contracts.py` and `src/annotations.py`.

## Auth

All endpoints use `bearerAuth` (HTTP Bearer JWT). Clerk will issue tokens later; until then local/dev can stub a JWT.

## How consumers use this

### Next.js (`web/`)

- Treat `openapi.yaml` as the source of truth for fetch clients and types (e.g. openapi-typescript or similar).
- Call Learning, Content, and Analysis from the app; never send country ground truth on analysis or annotation writes.
- Render attempt feedback from `PracticeAttemptResult.evidence_trail`, keeping **observations** (visual) distinct from **evidence** (geographic).

### Python analysis core (`src/`)

- Implement handlers that map JSON to/from existing dataclasses: `AnalysisResult`, `Observation`, `Evidence`, `CandidateScore`, `AnnotationRecord`.
- Keep labels out of the prediction path: analysis accepts image bytes only; annotation PATCH rejects `country_label`.
- Knowledge endpoints are read-only in MVP; claim versions may be referenced by `Evidence.claim_version_id`.

## Design invariants

1. Observation ≠ Evidence (separate arrays in analysis and learning responses).
2. Annotation write path has no country fields.
3. MVP endpoints only — no unused routes in this file.
