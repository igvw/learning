# Learning App v1 Implementation Plan

## Summary

Build a local, single-user learning app with a FastAPI API, a Svelte frontend, and SQLite storage. The app will import seed content from YAML/CSV at startup and via a manual CLI, but once content is in the app, new questions and revisions are stored in SQLite as the primary runtime source of truth. The first version optimizes for fast keyboard-first quiz flow, lightweight stats and maintenance, and a clean revision model that preserves history.

## Key Changes

### Project structure and runtime
- Use a two-app repo layout: `backend/` for FastAPI and `frontend/` for Svelte + Vite.
- Keep `content/` for seed files and `tests/` for backend and end-to-end coverage.
- Add `app.sh` to start backend and frontend together for local development.
- In development, run the Svelte app via Vite and the API via FastAPI; keep the browser-facing app as the Svelte frontend with `/api/*` calls to FastAPI.

### Content model and import flow
- Treat seed files as importable content, not the live canonical store after app edits begin.
- Use explicit stable IDs in seed files:
  - Module YAML fields: `source_id`, `title`, `parent_source_id`, `ui_copy` object.
  - Question CSV common fields: `source_id`, `module_source_id`, `type`, `ranking`, and type-specific fields.
- Import only missing seed modules/questions on startup and via a manual CLI command; do not overwrite existing DB records during v1 sync.
- Infer slugs from module titles on import and store them in the database.
- Seed 2 parent modules, each with 2 child modules and 5 questions per child, covering all question types and mixed rankings.

### Database and revision model
- Create tables for:
  - `modules`: hierarchy, slug, title, optional UI-copy metadata, optional `source_id`.
  - `questions`: logical question record, current module, manual `review_flag`, active version pointer.
  - `question_versions`: immutable revision history with prompt, type, ranking, type config, created timestamp.
  - `progress_buckets`: aggregate stats bucket for a question lineage.
  - `quiz_sessions`: module scope, requested question count, started/completed timestamps.
  - `quiz_session_items`: one row per asked question with submitted answer payload, correctness, and version used.
- Use `question_versions` for all edits. A revision never mutates prior content in place.
- When a revision is saved without reset, keep the same active `progress_bucket`.
- When a revision is saved with reset, create a new active `progress_bucket`, keep old buckets for historical reporting, and attach the new version to the new bucket.
- Keep manual review state on the logical question record so it survives revisions unless explicitly changed.

### Question types and evaluation rules
- Support three normalized question DTO types:
  - `single_text`: one input, multiple accepted answers.
  - `multi_text`: multiple required inputs, one accepted-answer set per input.
  - `inline_cloze`: prompt with ordered blanks rendered inline, one accepted-answer set per blank.
- Store type-specific configuration as structured JSON in the DB and normalized API payloads in the frontend.
- Apply the same answer normalization everywhere: trim outer whitespace, collapse repeated inner spaces, compare case-insensitively.
- Do not implement fuzzy matching in v1.
- Mark `multi_text` and `inline_cloze` correct only when every slot is correct.

### Quiz flow
- Make `/quiz` the default route.
- Selecting a parent module includes all descendant modules in the quiz scope.
- Start each quiz with 10 questions by default; if fewer active questions exist in scope, include all available questions.
- Lock the session question set at session creation time.
- Choose questions without replacement using weighted random sampling:
  - Base weight = `max(ranking, 1)`.
  - If the active progress bucket has zero attempts, double the weight.
  - Otherwise multiply by `(1 + incorrect_count) / (1 + correct_count)`.
- Show one active unanswered question at a time, but keep prior answered questions visible in a growing vertical stack.
- On submit, hide the submit control for that question, color the result state, and show canonical answers below the question.
- After the final submission, switch the page into a completed session state with summary stats and a prominent “start another quiz” action.

### Stats and maintenance flow
- Add a `/stats` route scoped to the currently selected module subtree.
- Show recent performance summary plus a question table with:
  - prompt preview
  - type
  - ranking
  - active version number
  - attempts
  - correct percentage
  - last asked timestamp
  - manual review flag
- Include a review-only filter that shows only manually flagged questions.
- Use a floating plus button to open a modal/drawer editor from stats.
- In the editor, support:
  - creating a question for any supported type
  - creating a new module inline
  - moving a question to a different module
  - toggling manual review
  - choosing whether a revision resets stats
  - viewing prior question versions in read-only form

### API surface
- `GET /api/modules/tree`: module hierarchy plus UI-copy metadata.
- `POST /api/modules`: create a module inline from the editor.
- `POST /api/quiz-sessions`: create a quiz session for a module scope and return ordered session items.
- `POST /api/quiz-sessions/{session_id}/items/{item_id}/submit`: evaluate and store one answer submission and return correctness plus canonical answers.
- `GET /api/stats?module_id=...&review_only=...`: recent summary plus question table rows for the selected scope.
- `POST /api/questions`: create a new logical question with version 1.
- `POST /api/questions/{question_id}/revisions`: create a new version, optionally move module, optionally reset stats.
- `GET /api/questions/{question_id}/versions`: list prior versions for the editor history view.

## Test Plan

- Backend unit tests for:
  - module import and hierarchy resolution
  - import idempotency for missing-only sync
  - answer normalization and correctness for all 3 question types
  - weighted quiz selection with deterministic seeded randomness
  - revision creation with and without stats reset
  - manual review flag persistence across revisions
  - stats aggregation by module subtree
- API tests for:
  - quiz session creation and answer submission
  - module inline creation
  - question create and revise flows
  - version history retrieval
- End-to-end tests for:
  - completing a quiz entirely by keyboard
  - seeing answered questions remain on screen with result styling
  - stats updating after a completed quiz
  - opening the stats editor drawer, creating a question, and revising a question
  - filtering the stats table to manually reviewed questions
- Smoke check that `./app.sh` starts the local app successfully.

## Assumptions

- v1 is local and single-user only; no auth or per-user data partitioning.
- App-created and app-revised content lives only in SQLite in v1; export back to YAML/CSV is out of scope.
- Seed import is additive only in v1; updating existing imported content from files is out of scope.
- Manual review flags affect the stats/maintenance workflow only and do not change quiz weighting in v1.
- The initial editor is a modal or drawer from stats, not a dedicated full-page editor route.
