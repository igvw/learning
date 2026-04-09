CREATE TABLE IF NOT EXISTS modules (
    id BIGSERIAL PRIMARY KEY,
    parent_id BIGINT REFERENCES modules(id) ON DELETE SET NULL,
    slug TEXT NOT NULL,
    full_slug TEXT NOT NULL UNIQUE,
    instruction TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_modules_parent_id ON modules(parent_id);

CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    module_id BIGINT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    rank INTEGER NOT NULL,
    type_config_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_module_id ON questions(module_id);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_review_flags (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    review_flag INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_user_review_flags_review
    ON user_review_flags(user_id, review_flag);

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
    score_earned REAL,
    score_possible REAL NOT NULL DEFAULT 1,
    resolved_prompt TEXT,
    resolved_type_config_json TEXT,
    submitted_answer_json TEXT,
    PRIMARY KEY (session_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_session_items_session_id
    ON quiz_session_items(session_id);

CREATE INDEX IF NOT EXISTS idx_quiz_session_items_question_id
    ON quiz_session_items(question_id);
