-- GeoMeta 001_init: core relational model for the MVP study / reasoning slice.
-- Implements entities and invariants from docs/04_DATA_MODEL.
-- Ground truth (actual_location_revisions) is evaluation-only; never an
-- analysis input. Absence of evidence is not contradiction (no DB default
-- that invents weakening contributions).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Ownership
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS profiles (
    profile_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name    TEXT NOT NULL DEFAULT 'local',
    clerk_user_id   TEXT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT profiles_status_check
        CHECK (status IN ('active', 'archived'))
);

CREATE TABLE IF NOT EXISTS study_sessions (
    session_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES profiles (profile_id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'active',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT study_sessions_status_check
        CHECK (status IN ('active', 'completed', 'abandoned', 'archived'))
);

CREATE INDEX IF NOT EXISTS study_sessions_profile_id_idx
    ON study_sessions (profile_id);

-- Pointer FKs added after child tables exist (same-round composite FKs).
CREATE TABLE IF NOT EXISTS rounds (
    round_id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id                  UUID NOT NULL
        REFERENCES study_sessions (session_id) ON DELETE CASCADE,
    status                      TEXT NOT NULL DEFAULT 'created',
    sequence_number             INTEGER,
    started_at                  TIMESTAMPTZ,
    ended_at                    TIMESTAMPTZ,
    current_guess_id            UUID,
    current_actual_location_id  UUID,
    current_evaluation_id       UUID,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rounds_status_check
        CHECK (status IN (
            'created',
            'active',
            'completed',
            'abandoned',
            'closed_without_guess'
        )),
    UNIQUE (round_id, session_id)
);

CREATE INDEX IF NOT EXISTS rounds_session_id_idx ON rounds (session_id);

-- ---------------------------------------------------------------------------
-- Geographic reference data
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS countries (
    country_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name  TEXT NOT NULL,
    external_code   TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT countries_status_check
        CHECK (status IN ('active', 'inactive', 'archived'))
);

CREATE UNIQUE INDEX IF NOT EXISTS countries_external_code_uidx
    ON countries (external_code)
    WHERE external_code IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS countries_active_name_uidx
    ON countries (canonical_name)
    WHERE status = 'active';

CREATE TABLE IF NOT EXISTS regions (
    region_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name      TEXT NOT NULL,
    country_id          UUID REFERENCES countries (country_id) ON DELETE SET NULL,
    region_type         TEXT NOT NULL DEFAULT 'administrative',
    description         TEXT,
    parent_region_id    UUID REFERENCES regions (region_id) ON DELETE SET NULL,
    status              TEXT NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT regions_type_check
        CHECK (region_type IN (
            'administrative',
            'broad_geographic',
            'physical',
            'climatic'
        )),
    CONSTRAINT regions_status_check
        CHECK (status IN ('active', 'archived'))
);

CREATE INDEX IF NOT EXISTS regions_country_id_idx ON regions (country_id);

CREATE TABLE IF NOT EXISTS region_aliases (
    region_alias_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id           UUID NOT NULL REFERENCES regions (region_id) ON DELETE CASCADE,
    alias_text          TEXT NOT NULL,
    language_or_context TEXT
);

CREATE INDEX IF NOT EXISTS region_aliases_region_id_idx
    ON region_aliases (region_id);

-- ---------------------------------------------------------------------------
-- Sources (imported images / captured frames)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sources (
    source_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type             TEXT NOT NULL,
    source_provenance       TEXT NOT NULL DEFAULT 'user_import',
    original_reference      TEXT,
    content_hash            TEXT NOT NULL,
    availability_status     TEXT NOT NULL DEFAULT 'available',
    unavailability_reason   TEXT,
    width                   INTEGER,
    height                  INTEGER,
    format                  TEXT,
    capture_timestamp       TIMESTAMPTZ,
    capture_stream_id       TEXT,
    frame_sequence_number   INTEGER,
    metadata_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT sources_type_check
        CHECK (source_type IN ('imported_image', 'captured_frame')),
    CONSTRAINT sources_provenance_check
        CHECK (source_provenance IN (
            'repository_sample',
            'external_dataset',
            'user_import',
            'live_capture'
        )),
    CONSTRAINT sources_availability_check
        CHECK (availability_status IN (
            'available',
            'unavailable',
            'hash_mismatch',
            'relink_pending'
        ))
);

CREATE INDEX IF NOT EXISTS sources_content_hash_idx ON sources (content_hash);

CREATE TABLE IF NOT EXISTS round_sources (
    round_source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id        UUID NOT NULL REFERENCES rounds (round_id) ON DELETE CASCADE,
    source_id       UUID NOT NULL REFERENCES sources (source_id) ON DELETE RESTRICT,
    sequence_number INTEGER NOT NULL,
    source_role     TEXT,
    associated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (round_id, source_id),
    UNIQUE (round_id, sequence_number)
);

-- ---------------------------------------------------------------------------
-- Scoring configuration (versioned)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS scoring_configurations (
    scoring_configuration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                     TEXT NOT NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scoring_configuration_versions (
    scoring_configuration_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scoring_configuration_id         UUID NOT NULL
        REFERENCES scoring_configurations (scoring_configuration_id) ON DELETE CASCADE,
    version_number                   INTEGER NOT NULL,
    parameters_json                  JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidate_inclusion_rule         TEXT NOT NULL DEFAULT '',
    aggregation_rule                 TEXT,
    missing_evidence_rule            TEXT NOT NULL DEFAULT '',
    contradiction_rule               TEXT NOT NULL DEFAULT '',
    created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    status                           TEXT NOT NULL DEFAULT 'draft',
    UNIQUE (scoring_configuration_id, version_number),
    CONSTRAINT scoring_configuration_versions_status_check
        CHECK (status IN ('draft', 'active', 'retired'))
);

-- ---------------------------------------------------------------------------
-- Geographic claims (versioned knowledge)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS geographic_claims (
    claim_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_type  TEXT NOT NULL DEFAULT 'association',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT geographic_claims_type_check
        CHECK (claim_type IN ('association', 'exclusion', 'other'))
);

CREATE TABLE IF NOT EXISTS geographic_claim_versions (
    claim_version_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id                    UUID NOT NULL
        REFERENCES geographic_claims (claim_id) ON DELETE CASCADE,
    version_number              INTEGER NOT NULL,
    claim_content               TEXT NOT NULL,
    country_id                  UUID REFERENCES countries (country_id) ON DELETE SET NULL,
    region_id                   UUID REFERENCES regions (region_id) ON DELETE SET NULL,
    geographic_scope            TEXT,
    source_title                TEXT,
    source_reference            TEXT,
    review_status               TEXT NOT NULL DEFAULT 'proposed',
    claim_truth_confidence      DOUBLE PRECISION,
    source_reliability          DOUBLE PRECISION,
    scoring_strength            DOUBLE PRECISION,
    supersedes_claim_version_id UUID
        REFERENCES geographic_claim_versions (claim_version_id) ON DELETE SET NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at                 TIMESTAMPTZ,
    UNIQUE (claim_id, version_number),
    CONSTRAINT geographic_claim_versions_review_status_check
        CHECK (review_status IN (
            'proposed',
            'approved',
            'rejected',
            'deprecated'
        ))
);

CREATE INDEX IF NOT EXISTS geographic_claim_versions_claim_id_idx
    ON geographic_claim_versions (claim_id);

CREATE INDEX IF NOT EXISTS geographic_claim_versions_approved_idx
    ON geographic_claim_versions (review_status)
    WHERE review_status = 'approved';

-- ---------------------------------------------------------------------------
-- Analyses and detector outputs
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analyses (
    analysis_id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id                            UUID NOT NULL
        REFERENCES rounds (round_id) ON DELETE CASCADE,
    status                              TEXT NOT NULL DEFAULT 'processing',
    detector_version                    TEXT,
    detector_schema_version             TEXT,
    measurement_schema_version          TEXT,
    observation_schema_version          TEXT,
    scoring_configuration_version_id    UUID
        REFERENCES scoring_configuration_versions (scoring_configuration_version_id)
        ON DELETE SET NULL,
    candidate_inclusion_rule            TEXT,
    aggregation_rule                    TEXT,
    analysis_manifest_json              JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at                        TIMESTAMPTZ,
    insufficient_reason                 TEXT,
    failure_code                        TEXT,
    diagnostic_summary                  TEXT,
    capture_sequence_start              INTEGER,
    capture_sequence_end                INTEGER,
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT analyses_status_check
        CHECK (status IN (
            'processing',
            'completed',
            'insufficient_evidence',
            'failed',
            'timed_out',
            'cancelled'
        )),
    UNIQUE (analysis_id, round_id)
);

CREATE INDEX IF NOT EXISTS analyses_round_id_idx ON analyses (round_id);
CREATE INDEX IF NOT EXISTS analyses_status_idx ON analyses (status);

CREATE TABLE IF NOT EXISTS analysis_sources (
    analysis_source_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id             UUID NOT NULL REFERENCES analyses (analysis_id) ON DELETE CASCADE,
    source_id               UUID NOT NULL REFERENCES sources (source_id) ON DELETE RESTRICT,
    sequence_number         INTEGER NOT NULL,
    source_role             TEXT,
    input_content_hash      TEXT NOT NULL,
    input_metadata_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (analysis_id, source_id),
    UNIQUE (analysis_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS analysis_claim_versions (
    analysis_id       UUID NOT NULL REFERENCES analyses (analysis_id) ON DELETE CASCADE,
    claim_version_id  UUID NOT NULL
        REFERENCES geographic_claim_versions (claim_version_id) ON DELETE RESTRICT,
    PRIMARY KEY (analysis_id, claim_version_id)
);

CREATE TABLE IF NOT EXISTS image_regions (
    region_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES sources (source_id) ON DELETE CASCADE,
    region_type     TEXT NOT NULL DEFAULT 'full_image',
    left_coord      DOUBLE PRECISION,
    top_coord       DOUBLE PRECISION,
    right_coord     DOUBLE PRECISION,
    bottom_coord    DOUBLE PRECISION,
    region_version  TEXT,
    CONSTRAINT image_regions_type_check
        CHECK (region_type IN (
            'full_image',
            'top_third',
            'middle_third',
            'bottom_third',
            'bounding_box'
        ))
);

CREATE INDEX IF NOT EXISTS image_regions_source_id_idx ON image_regions (source_id);

CREATE TABLE IF NOT EXISTS measurements (
    measurement_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id                 UUID NOT NULL REFERENCES analyses (analysis_id) ON DELETE CASCADE,
    source_id                   UUID REFERENCES sources (source_id) ON DELETE SET NULL,
    region_id                   UUID REFERENCES image_regions (region_id) ON DELETE SET NULL,
    feature_name                TEXT NOT NULL,
    numeric_value               DOUBLE PRECISION NOT NULL,
    unit                        TEXT,
    measurement_schema_version  TEXT,
    detector_version            TEXT
);

CREATE INDEX IF NOT EXISTS measurements_analysis_id_idx ON measurements (analysis_id);

CREATE TABLE IF NOT EXISTS observations (
    observation_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id             UUID NOT NULL REFERENCES analyses (analysis_id) ON DELETE CASCADE,
    observation_type        TEXT NOT NULL,
    value_json              JSONB NOT NULL DEFAULT '{}'::jsonb,
    state                   TEXT NOT NULL DEFAULT 'ambiguous',
    observation_confidence  DOUBLE PRECISION,
    detector_version        TEXT,
    region_id               UUID REFERENCES image_regions (region_id) ON DELETE SET NULL,
    deduplication_key       TEXT,
    CONSTRAINT observations_state_check
        CHECK (state IN ('positive', 'ambiguous', 'absent', 'conflicting'))
);

CREATE INDEX IF NOT EXISTS observations_analysis_id_idx ON observations (analysis_id);

CREATE TABLE IF NOT EXISTS observation_measurements (
    observation_id      UUID NOT NULL REFERENCES observations (observation_id) ON DELETE CASCADE,
    measurement_id      UUID NOT NULL REFERENCES measurements (measurement_id) ON DELETE CASCADE,
    relationship_type   TEXT NOT NULL DEFAULT 'supporting',
    PRIMARY KEY (observation_id, measurement_id)
);

CREATE TABLE IF NOT EXISTS raw_detector_outputs (
    raw_output_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id             UUID NOT NULL REFERENCES analyses (analysis_id) ON DELETE CASCADE,
    detector_name           TEXT NOT NULL,
    detector_version        TEXT,
    payload_schema_version  TEXT,
    payload_reference       TEXT,
    payload_json            JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS raw_detector_outputs_analysis_id_idx
    ON raw_detector_outputs (analysis_id);

-- ---------------------------------------------------------------------------
-- Evidence, candidate scores, contributions
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id         UUID NOT NULL REFERENCES analyses (analysis_id) ON DELETE CASCADE,
    observation_id      UUID REFERENCES observations (observation_id) ON DELETE SET NULL,
    claim_version_id    UUID
        REFERENCES geographic_claim_versions (claim_version_id) ON DELETE SET NULL,
    region_id           UUID REFERENCES image_regions (region_id) ON DELETE SET NULL,
    evidence_type       TEXT NOT NULL,
    value_json          JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence          DOUBLE PRECISION,
    strength            DOUBLE PRECISION,
    reliability         DOUBLE PRECISION,
    diagnosticity       DOUBLE PRECISION,
    geographic_scope    TEXT,
    direction           TEXT NOT NULL DEFAULT 'inconclusive',
    deduplication_key   TEXT,
    provenance_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT evidence_direction_check
        CHECK (direction IN (
            'supporting',
            'weakening',
            'inconclusive',
            'conflicting'
        )),
    UNIQUE (evidence_id, analysis_id)
);

CREATE INDEX IF NOT EXISTS evidence_analysis_id_idx ON evidence (analysis_id);

CREATE TABLE IF NOT EXISTS candidate_scores (
    candidate_score_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id                 UUID NOT NULL REFERENCES analyses (analysis_id) ON DELETE CASCADE,
    candidate_type              TEXT NOT NULL,
    country_id                  UUID REFERENCES countries (country_id) ON DELETE RESTRICT,
    region_id                   UUID REFERENCES regions (region_id) ON DELETE RESTRICT,
    ranking_context_country_id  UUID REFERENCES countries (country_id) ON DELETE SET NULL,
    total_score                 DOUBLE PRECISION NOT NULL DEFAULT 0,
    display_rank                INTEGER,
    display_status              TEXT NOT NULL DEFAULT 'included',
    inclusion_reason            TEXT,
    evidence_quality_summary    JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT candidate_scores_type_check
        CHECK (candidate_type IN ('country', 'region')),
    CONSTRAINT candidate_scores_display_status_check
        CHECK (display_status IN ('included', 'excluded')),
    CONSTRAINT candidate_scores_target_check
        CHECK (
            (candidate_type = 'country'
                AND country_id IS NOT NULL
                AND region_id IS NULL)
            OR
            (candidate_type = 'region'
                AND region_id IS NOT NULL
                AND country_id IS NULL
                AND ranking_context_country_id IS NOT NULL)
        ),
    UNIQUE (candidate_score_id, analysis_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS candidate_scores_country_uidx
    ON candidate_scores (analysis_id, candidate_type, country_id)
    WHERE candidate_type = 'country';

CREATE UNIQUE INDEX IF NOT EXISTS candidate_scores_region_uidx
    ON candidate_scores (analysis_id, candidate_type, region_id)
    WHERE candidate_type = 'region';

CREATE INDEX IF NOT EXISTS candidate_scores_analysis_id_idx
    ON candidate_scores (analysis_id);

CREATE TABLE IF NOT EXISTS score_contributions (
    score_contribution_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_score_id      UUID NOT NULL,
    analysis_id             UUID NOT NULL,
    evidence_id             UUID NOT NULL,
    claim_version_id        UUID
        REFERENCES geographic_claim_versions (claim_version_id) ON DELETE SET NULL,
    contribution_value      DOUBLE PRECISION NOT NULL DEFAULT 0,
    direction               TEXT NOT NULL DEFAULT 'neutral',
    weight_details_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
    calculation_version     TEXT,
    reason                  TEXT,
    CONSTRAINT score_contributions_direction_check
        CHECK (direction IN (
            'supporting',
            'weakening',
            'conflicting',
            'neutral'
        )),
    CONSTRAINT score_contributions_candidate_fk
        FOREIGN KEY (candidate_score_id, analysis_id)
        REFERENCES candidate_scores (candidate_score_id, analysis_id)
        ON DELETE CASCADE,
    CONSTRAINT score_contributions_evidence_fk
        FOREIGN KEY (evidence_id, analysis_id)
        REFERENCES evidence (evidence_id, analysis_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS score_contributions_candidate_score_id_idx
    ON score_contributions (candidate_score_id);

CREATE INDEX IF NOT EXISTS score_contributions_evidence_id_idx
    ON score_contributions (evidence_id);

-- ---------------------------------------------------------------------------
-- Study checkpoints (explanation requests)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS study_checkpoints (
    checkpoint_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id                    UUID NOT NULL REFERENCES rounds (round_id) ON DELETE CASCADE,
    analysis_id                 UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    hint_level                  TEXT,
    display_snapshot_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
    checkpoint_schema_version   TEXT,
    CONSTRAINT study_checkpoints_analysis_fk
        FOREIGN KEY (analysis_id, round_id)
        REFERENCES analyses (analysis_id, round_id)
        ON DELETE RESTRICT,
    UNIQUE (checkpoint_id, round_id)
);

CREATE INDEX IF NOT EXISTS study_checkpoints_round_id_idx
    ON study_checkpoints (round_id);

CREATE INDEX IF NOT EXISTS study_checkpoints_analysis_id_idx
    ON study_checkpoints (analysis_id);

-- ---------------------------------------------------------------------------
-- Player guesses and actual locations (evaluation-only ground truth)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS player_guess_revisions (
    guess_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id                UUID NOT NULL REFERENCES rounds (round_id) ON DELETE CASCADE,
    original_country_input  TEXT,
    country_id              UUID REFERENCES countries (country_id) ON DELETE SET NULL,
    original_region_input   TEXT,
    region_id               UUID REFERENCES regions (region_id) ON DELETE SET NULL,
    submitted_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    note                    TEXT,
    status                  TEXT NOT NULL DEFAULT 'current',
    supersedes_guess_id     UUID,
    CONSTRAINT player_guess_revisions_status_check
        CHECK (status IN ('current', 'superseded', 'withdrawn')),
    UNIQUE (round_id, guess_id)
);

CREATE INDEX IF NOT EXISTS player_guess_revisions_round_id_idx
    ON player_guess_revisions (round_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'player_guess_revisions_supersedes_same_round_fk'
    ) THEN
        ALTER TABLE player_guess_revisions
            ADD CONSTRAINT player_guess_revisions_supersedes_same_round_fk
            FOREIGN KEY (round_id, supersedes_guess_id)
            REFERENCES player_guess_revisions (round_id, guess_id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS actual_location_revisions (
    actual_location_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id                        UUID NOT NULL REFERENCES rounds (round_id) ON DELETE CASCADE,
    original_country_input          TEXT,
    country_id                      UUID REFERENCES countries (country_id) ON DELETE SET NULL,
    original_region_input           TEXT,
    region_id                       UUID REFERENCES regions (region_id) ON DELETE SET NULL,
    verification_status             TEXT NOT NULL DEFAULT 'provisional',
    entered_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    provenance_note                 TEXT,
    supersedes_actual_location_id   UUID,
    CONSTRAINT actual_location_revisions_verification_check
        CHECK (verification_status IN (
            'provisional',
            'verified',
            'corrected',
            'rejected'
        )),
    UNIQUE (round_id, actual_location_id)
);

CREATE INDEX IF NOT EXISTS actual_location_revisions_round_id_idx
    ON actual_location_revisions (round_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'actual_location_revisions_supersedes_same_round_fk'
    ) THEN
        ALTER TABLE actual_location_revisions
            ADD CONSTRAINT actual_location_revisions_supersedes_same_round_fk
            FOREIGN KEY (round_id, supersedes_actual_location_id)
            REFERENCES actual_location_revisions (round_id, actual_location_id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id                    UUID NOT NULL REFERENCES rounds (round_id) ON DELETE CASCADE,
    analysis_id                 UUID NOT NULL,
    checkpoint_id               UUID,
    guess_id                    UUID NOT NULL,
    actual_location_id          UUID NOT NULL,
    country_result              TEXT NOT NULL DEFAULT 'unevaluated',
    regional_result             TEXT NOT NULL DEFAULT 'unevaluated',
    correct_country_rank        INTEGER,
    granularity_note            TEXT,
    evaluation_rule_version     TEXT NOT NULL,
    supersedes_evaluation_id    UUID,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    status                      TEXT NOT NULL DEFAULT 'current',
    CONSTRAINT evaluations_country_result_check
        CHECK (country_result IN ('correct', 'incorrect', 'unevaluated')),
    CONSTRAINT evaluations_regional_result_check
        CHECK (regional_result IN ('correct', 'incorrect', 'unevaluated')),
    CONSTRAINT evaluations_status_check
        CHECK (status IN ('current', 'superseded')),
    UNIQUE (round_id, evaluation_id)
);

CREATE INDEX IF NOT EXISTS evaluations_round_id_idx ON evaluations (round_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'evaluations_analysis_same_round_fk'
    ) THEN
        ALTER TABLE evaluations
            ADD CONSTRAINT evaluations_analysis_same_round_fk
            FOREIGN KEY (analysis_id, round_id)
            REFERENCES analyses (analysis_id, round_id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'evaluations_checkpoint_same_round_fk'
    ) THEN
        ALTER TABLE evaluations
            ADD CONSTRAINT evaluations_checkpoint_same_round_fk
            FOREIGN KEY (checkpoint_id, round_id)
            REFERENCES study_checkpoints (checkpoint_id, round_id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'evaluations_guess_same_round_fk'
    ) THEN
        ALTER TABLE evaluations
            ADD CONSTRAINT evaluations_guess_same_round_fk
            FOREIGN KEY (round_id, guess_id)
            REFERENCES player_guess_revisions (round_id, guess_id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'evaluations_actual_same_round_fk'
    ) THEN
        ALTER TABLE evaluations
            ADD CONSTRAINT evaluations_actual_same_round_fk
            FOREIGN KEY (round_id, actual_location_id)
            REFERENCES actual_location_revisions (round_id, actual_location_id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'evaluations_supersedes_same_round_fk'
    ) THEN
        ALTER TABLE evaluations
            ADD CONSTRAINT evaluations_supersedes_same_round_fk
            FOREIGN KEY (round_id, supersedes_evaluation_id)
            REFERENCES evaluations (round_id, evaluation_id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- Same-round authoritative pointers on rounds
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'rounds_current_guess_same_round_fk'
    ) THEN
        ALTER TABLE rounds
            ADD CONSTRAINT rounds_current_guess_same_round_fk
            FOREIGN KEY (round_id, current_guess_id)
            REFERENCES player_guess_revisions (round_id, guess_id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'rounds_current_actual_same_round_fk'
    ) THEN
        ALTER TABLE rounds
            ADD CONSTRAINT rounds_current_actual_same_round_fk
            FOREIGN KEY (round_id, current_actual_location_id)
            REFERENCES actual_location_revisions (round_id, actual_location_id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'rounds_current_evaluation_same_round_fk'
    ) THEN
        ALTER TABLE rounds
            ADD CONSTRAINT rounds_current_evaluation_same_round_fk
            FOREIGN KEY (round_id, current_evaluation_id)
            REFERENCES evaluations (round_id, evaluation_id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- Current actual-location pointer must reference a verified revision.
CREATE OR REPLACE FUNCTION enforce_current_actual_location_verified()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.current_actual_location_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM actual_location_revisions alr
        WHERE alr.round_id = NEW.round_id
          AND alr.actual_location_id = NEW.current_actual_location_id
          AND alr.verification_status = 'verified'
    ) THEN
        RAISE EXCEPTION
            'rounds.current_actual_location_id must reference a verified actual_location_revision for the same round';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS rounds_current_actual_verified_trg ON rounds;
CREATE TRIGGER rounds_current_actual_verified_trg
    BEFORE INSERT OR UPDATE OF current_actual_location_id
    ON rounds
    FOR EACH ROW
    EXECUTE FUNCTION enforce_current_actual_location_verified();

-- ---------------------------------------------------------------------------
-- Learning insight snapshots (derived; not source of truth)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS learning_insight_snapshots (
    insight_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id              UUID NOT NULL REFERENCES profiles (profile_id) ON DELETE CASCADE,
    insight_type            TEXT NOT NULL,
    content                 TEXT NOT NULL,
    insight_rule_version    TEXT NOT NULL,
    query_scope_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
    sample_size             INTEGER,
    aggregate_metrics_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    uncertainty_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
    status                  TEXT NOT NULL DEFAULT 'current',
    supersedes_insight_id   UUID
        REFERENCES learning_insight_snapshots (insight_id) ON DELETE SET NULL,
    generated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT learning_insight_snapshots_type_check
        CHECK (insight_type IN ('descriptive', 'preliminary', 'stronger_claim')),
    CONSTRAINT learning_insight_snapshots_status_check
        CHECK (status IN ('current', 'stale', 'superseded', 'invalidated'))
);

CREATE INDEX IF NOT EXISTS learning_insight_snapshots_profile_id_idx
    ON learning_insight_snapshots (profile_id);

CREATE TABLE IF NOT EXISTS learning_insight_support (
    insight_support_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_id          UUID NOT NULL
        REFERENCES learning_insight_snapshots (insight_id) ON DELETE CASCADE,
    round_id            UUID REFERENCES rounds (round_id) ON DELETE SET NULL,
    analysis_id         UUID REFERENCES analyses (analysis_id) ON DELETE SET NULL,
    evaluation_id       UUID,
    support_role        TEXT
);

CREATE INDEX IF NOT EXISTS learning_insight_support_insight_id_idx
    ON learning_insight_support (insight_id);
