# Database

Local PostgreSQL is the learning/product system of record for GeoMeta.
Schema follows `docs/04_DATA_MODEL` (normalized study/reasoning tables) plus
`002_learning.sql` for lessons, practice, and mastery.

Object storage for images and Redis are planned later; they are not required
for this schema.

## Start Postgres

From the repo root:

```powershell
docker compose up -d db
```

Defaults (local-only, not for production):

| Setting  | Value     |
|----------|-----------|
| host     | localhost |
| port     | 5432      |
| user     | geometa   |
| password | geometa   |
| database | geometa   |

Connection URL:

```text
postgresql://geometa:geometa@localhost:5432/geometa
```

Check readiness:

```powershell
docker compose ps
docker compose exec db pg_isready -U geometa -d geometa
```

## Apply migrations

`docker-compose.yml` mounts `001_init.sql` into
`/docker-entrypoint-initdb.d/`, so the core schema runs automatically the first
time the `geometa_pgdata` volume is created. Apply the learning migration after
the DB is up:

```powershell
# One-liner: apply both migrations (safe IF NOT EXISTS where used)
Get-Content db\migrations\001_init.sql, db\migrations\002_learning.sql -Raw |
  docker compose exec -T db psql -U geometa -d geometa
```

Or apply individually:

```powershell
Get-Content db\migrations\001_init.sql -Raw |
  docker compose exec -T db psql -U geometa -d geometa

Get-Content db\migrations\002_learning.sql -Raw |
  docker compose exec -T db psql -U geometa -d geometa
```

Fresh volume bootstrap: `docker compose up -d db` creates the DB and runs
`001_init.sql` once. Then run the `002_learning.sql` command above.

To re-bootstrap from scratch (destructive):

```powershell
docker compose down -v
docker compose up -d db
# wait until healthy, then apply 002
Get-Content db\migrations\002_learning.sql -Raw |
  docker compose exec -T db psql -U geometa -d geometa
```

## Schema overview

### `001_init.sql` (core)

| Table | Role |
|-------|------|
| `profiles` | Local owner; optional nullable `clerk_user_id` |
| `study_sessions` | Session lifecycle container |
| `rounds` | One location task; authoritative current-record pointers |
| `countries` / `regions` / `region_aliases` | Candidate geography |
| `sources` / `round_sources` | Imported/captured images and round association |
| `scoring_configurations` / `_versions` | Versioned scoring rules |
| `geographic_claims` / `geographic_claim_versions` | Versioned knowledge |
| `analyses` / `analysis_sources` / `analysis_claim_versions` | Immutable analysis attempts |
| `image_regions` / `measurements` / `observations` | Detector outputs |
| `observation_measurements` / `raw_detector_outputs` | Links + optional raw audit |
| `evidence` / `candidate_scores` / `score_contributions` | Traceable ranking |
| `study_checkpoints` | Explanation-request snapshots |
| `player_guess_revisions` | Player guesses (not prediction inputs) |
| `actual_location_revisions` | Ground truth (evaluation-only) |
| `evaluations` | Immutable prediction vs guess vs actual |
| `learning_insight_snapshots` / `_support` | Derived insight history |

### `002_learning.sql` (practice / mastery)

| Table | Role |
|-------|------|
| `lessons` | Learnable content, optional claim link |
| `meta_paths` / `meta_path_lessons` | Ordered lesson paths |
| `practice_sessions` / `practice_attempts` | Drill attempts |
| `meta_mastery` | Spaced-review mastery per claim/lesson |
| `lesson_progress` | Per-profile lesson completion |

## Stop / reset

```powershell
docker compose stop db
```

Wipe local data (destructive):

```powershell
docker compose down -v
```
