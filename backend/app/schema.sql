CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    password_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id);

CREATE TABLE IF NOT EXISTS modules (
    id BIGSERIAL PRIMARY KEY,
    parent_id BIGINT REFERENCES modules(id) ON DELETE SET NULL,
    slug TEXT NOT NULL,
    full_slug TEXT NOT NULL,
    instruction TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    admin_verified INTEGER NOT NULL DEFAULT 1,
    moderation_status TEXT NOT NULL DEFAULT 'verified',
    admin_review_note TEXT NOT NULL DEFAULT '',
    reviewed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_modules_parent_id ON modules(parent_id);
CREATE INDEX IF NOT EXISTS idx_modules_created_by_status
    ON modules(created_by_user_id, admin_verified, moderation_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_verified_full_slug
    ON modules (LOWER(full_slug))
    WHERE admin_verified = 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_pending_owner_full_slug
    ON modules (created_by_user_id, LOWER(full_slug))
    WHERE admin_verified = 0
      AND created_by_user_id IS NOT NULL
      AND moderation_status = 'pending';

CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    module_id BIGINT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    prompt_key TEXT NOT NULL,
    rank INTEGER NOT NULL,
    type_config_json TEXT NOT NULL,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    admin_verified INTEGER NOT NULL DEFAULT 1,
    moderation_status TEXT NOT NULL DEFAULT 'verified',
    admin_review_note TEXT NOT NULL DEFAULT '',
    reviewed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    replaced_by_question_id BIGINT REFERENCES questions(id) ON DELETE SET NULL,
    progress_from_question_id BIGINT REFERENCES questions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_module_id ON questions(module_id);
CREATE INDEX IF NOT EXISTS idx_questions_module_prompt_key ON questions(module_id, prompt_key);
CREATE INDEX IF NOT EXISTS idx_questions_prompt_key ON questions(prompt_key);
CREATE INDEX IF NOT EXISTS idx_questions_created_by_status
    ON questions(created_by_user_id, admin_verified, moderation_status);
CREATE INDEX IF NOT EXISTS idx_questions_enabled_module
    ON questions(module_id, enabled, moderation_status);
CREATE INDEX IF NOT EXISTS idx_questions_replaced_by
    ON questions(replaced_by_question_id);
CREATE INDEX IF NOT EXISTS idx_questions_progress_from
    ON questions(progress_from_question_id);

CREATE TABLE IF NOT EXISTS question_bundles (
    id BIGSERIAL PRIMARY KEY,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    variant_index INTEGER NOT NULL,
    prompt_values_json TEXT NOT NULL,
    accepted_answers_json TEXT NOT NULL,
    UNIQUE(question_id, variant_index),
    UNIQUE(id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_question_bundles_question_id
    ON question_bundles(question_id, variant_index);

CREATE OR REPLACE VIEW question_bundle_summaries AS
SELECT
    question_id,
    json_agg(
        json_build_object(
            'prompt_values', prompt_values_json::json,
            'accepted_answers', accepted_answers_json::json
        )
        ORDER BY variant_index ASC
    )::text AS variants_json
FROM question_bundles
GROUP BY question_id;

CREATE TABLE IF NOT EXISTS question_revision_proposals (
    id BIGSERIAL PRIMARY KEY,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    proposer_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    question_type TEXT NOT NULL,
    type_config_json TEXT NOT NULL,
    delete_requested INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    admin_review_note TEXT NOT NULL DEFAULT '',
    reviewed_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(question_id, proposer_user_id)
);

CREATE INDEX IF NOT EXISTS idx_question_revision_proposals_proposer
    ON question_revision_proposals(proposer_user_id, status);
CREATE INDEX IF NOT EXISTS idx_question_revision_proposals_question
    ON question_revision_proposals(question_id, status);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id BIGINT REFERENCES modules(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_module_created
    ON quiz_sessions(user_id, module_id, created_at);

CREATE TABLE IF NOT EXISTS quiz_session_items (
    session_id BIGINT NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    bundle_variant_id BIGINT,
    score_earned REAL,
    score_possible REAL NOT NULL DEFAULT 1,
    resolved_prompt TEXT,
    resolved_type_config_json TEXT,
    submitted_answer_json TEXT,
    PRIMARY KEY (session_id, question_id),
    FOREIGN KEY (bundle_variant_id, question_id) REFERENCES question_bundles(id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_session_items_session_id
    ON quiz_session_items(session_id);

CREATE INDEX IF NOT EXISTS idx_quiz_session_items_question_id
    ON quiz_session_items(question_id);

CREATE TABLE IF NOT EXISTS attempts (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
    module_id BIGINT REFERENCES modules(id) ON DELETE SET NULL,
    bundle_variant_id BIGINT,
    score_earned REAL NOT NULL,
    score_possible REAL NOT NULL DEFAULT 1,
    submitted_answer_json TEXT,
    answered_at TEXT NOT NULL,
    UNIQUE(session_id, question_id),
    FOREIGN KEY (bundle_variant_id, question_id) REFERENCES question_bundles(id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_attempts_user_question_answered
    ON attempts(user_id, question_id, answered_at);

CREATE INDEX IF NOT EXISTS idx_attempts_user_session
    ON attempts(user_id, session_id);

CREATE INDEX IF NOT EXISTS idx_attempts_question_id
    ON attempts(question_id);

CREATE INDEX IF NOT EXISTS idx_attempts_bundle_variant_id
    ON attempts(bundle_variant_id);
