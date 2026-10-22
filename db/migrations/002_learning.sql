-- GeoMeta 002_learning: interactive learnable metas (lessons, practice, mastery).
-- Naming kept consistent with profiles / geographic_claims from 001_init.
-- Lighter than a full curriculum product model; expand when 04_DATA_MODEL adds it.

-- ---------------------------------------------------------------------------
-- Lessons and meta learning paths
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS lessons (
    lesson_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL DEFAULT '',
    body_markdown   TEXT NOT NULL DEFAULT '',
    claim_id        UUID REFERENCES geographic_claims (claim_id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'draft',
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT lessons_status_check
        CHECK (status IN ('draft', 'published', 'archived'))
);

CREATE INDEX IF NOT EXISTS lessons_claim_id_idx ON lessons (claim_id);

CREATE TABLE IF NOT EXISTS meta_paths (
    meta_path_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'draft',
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT meta_paths_status_check
        CHECK (status IN ('draft', 'published', 'archived'))
);

CREATE TABLE IF NOT EXISTS meta_path_lessons (
    meta_path_id    UUID NOT NULL REFERENCES meta_paths (meta_path_id) ON DELETE CASCADE,
    lesson_id       UUID NOT NULL REFERENCES lessons (lesson_id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    PRIMARY KEY (meta_path_id, lesson_id),
    UNIQUE (meta_path_id, sequence_number)
);

-- ---------------------------------------------------------------------------
-- Practice (separate from study_sessions; drills against learnable metas)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS practice_sessions (
    practice_session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES profiles (profile_id) ON DELETE CASCADE,
    meta_path_id        UUID REFERENCES meta_paths (meta_path_id) ON DELETE SET NULL,
    lesson_id           UUID REFERENCES lessons (lesson_id) ON DELETE SET NULL,
    mode                TEXT NOT NULL DEFAULT 'free_practice',
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at            TIMESTAMPTZ,
    CONSTRAINT practice_sessions_mode_check
        CHECK (mode IN (
            'free_practice',
            'lesson_drill',
            'path_drill',
            'spaced_review'
        ))
);

CREATE INDEX IF NOT EXISTS practice_sessions_profile_id_idx
    ON practice_sessions (profile_id);

CREATE TABLE IF NOT EXISTS practice_attempts (
    practice_attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    practice_session_id UUID NOT NULL
        REFERENCES practice_sessions (practice_session_id) ON DELETE CASCADE,
    profile_id          UUID NOT NULL REFERENCES profiles (profile_id) ON DELETE CASCADE,
    lesson_id           UUID REFERENCES lessons (lesson_id) ON DELETE SET NULL,
    claim_id            UUID REFERENCES geographic_claims (claim_id) ON DELETE SET NULL,
    source_id           UUID REFERENCES sources (source_id) ON DELETE SET NULL,
    analysis_id         UUID REFERENCES analyses (analysis_id) ON DELETE SET NULL,
    prompt_json         JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_correct          BOOLEAN,
    score_delta         DOUBLE PRECISION,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS practice_attempts_session_id_idx
    ON practice_attempts (practice_session_id);

CREATE INDEX IF NOT EXISTS practice_attempts_profile_id_idx
    ON practice_attempts (profile_id);

CREATE INDEX IF NOT EXISTS practice_attempts_lesson_id_idx
    ON practice_attempts (lesson_id);

-- ---------------------------------------------------------------------------
-- Mastery / progress (spaced review signals)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS meta_mastery (
    mastery_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES profiles (profile_id) ON DELETE CASCADE,
    -- Exactly one of claim_id or lesson_id identifies the mastery target.
    claim_id        UUID REFERENCES geographic_claims (claim_id) ON DELETE CASCADE,
    lesson_id       UUID REFERENCES lessons (lesson_id) ON DELETE CASCADE,
    mastery_key     TEXT NOT NULL,
    mastery_score   DOUBLE PRECISION NOT NULL DEFAULT 0,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    correct_count   INTEGER NOT NULL DEFAULT 0,
    next_review_at  TIMESTAMPTZ,
    last_practiced_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, mastery_key),
    CONSTRAINT meta_mastery_score_range
        CHECK (mastery_score >= 0 AND mastery_score <= 1),
    CONSTRAINT meta_mastery_counts_check
        CHECK (
            attempt_count >= 0
            AND correct_count >= 0
            AND correct_count <= attempt_count
        ),
    CONSTRAINT meta_mastery_target_check
        CHECK (
            (claim_id IS NOT NULL AND lesson_id IS NULL)
            OR (claim_id IS NULL AND lesson_id IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS meta_mastery_profile_id_idx ON meta_mastery (profile_id);
CREATE INDEX IF NOT EXISTS meta_mastery_next_review_at_idx
    ON meta_mastery (next_review_at);

CREATE TABLE IF NOT EXISTS lesson_progress (
    lesson_progress_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES profiles (profile_id) ON DELETE CASCADE,
    lesson_id           UUID NOT NULL REFERENCES lessons (lesson_id) ON DELETE CASCADE,
    meta_path_id        UUID REFERENCES meta_paths (meta_path_id) ON DELETE SET NULL,
    status              TEXT NOT NULL DEFAULT 'not_started',
    completion_pct      DOUBLE PRECISION NOT NULL DEFAULT 0,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, lesson_id),
    CONSTRAINT lesson_progress_status_check
        CHECK (status IN (
            'not_started',
            'in_progress',
            'completed',
            'needs_review'
        )),
    CONSTRAINT lesson_progress_pct_range
        CHECK (completion_pct >= 0 AND completion_pct <= 1)
);

CREATE INDEX IF NOT EXISTS lesson_progress_profile_id_idx
    ON lesson_progress (profile_id);
