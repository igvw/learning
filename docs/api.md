# Learning App API

This document describes the current API surface by capability.

See also:

- [Overview](overview.md)
- [Database](database.md)
- [UI](ui.md)

## Conventions

- all app routes live under `/api`
- request and response bodies are JSON unless otherwise noted
- `question_type` is one of `single_text`, `computed_text`, `multi_text`, `ordered_multi`, `inline_cloze`
- user-scoped quiz, stats, and review routes require `X-User-Id`

## Modules

### `GET /api/modules/tree`

Returns the full module tree.

Each node includes:

- `id`
- `title`
- `slug`
- `full_slug`
- `instruction`
- `children`

### `POST /api/modules`

Creates one module node.

Practical request shape:

```json
{
  "title": "nouns_to_english",
  "parent_id": 12,
  "instruction": "Translate each Norwegian noun into English."
}
```

The frontend builds slash-path `mkdir -p` behavior by making repeated calls.

## Users

### `GET /api/users`

Returns the current user list.

### `POST /api/users`

Creates one study user.

Practical request shape:

```json
{
  "handle": "ignazio",
  "display_name": "Ignazio"
}
```

## Quiz Sessions

### `POST /api/quiz-sessions`

Starts a quiz session for the active user.

Requires `X-User-Id`.

Practical request shape:

```json
{
  "module_id": 12,
  "count": 10
}
```

Response includes:

- session `id`
- selected `module_id`
- `completed_at`
- `items[]`

Each quiz item includes:

- question and module identifiers
- module instruction
- prompt and question type
- rank
- normalized `type_config`
- current answer state fields

### `POST /api/quiz-sessions/{session_id}/items/{item_id}/submit`

Submits one answered question.

Practical request shape:

```json
{
  "answers": ["white nile", "blue nile"]
}
```

Response includes:

- `item_id`
- `is_correct`
- `score_earned`
- `score_possible`
- `slot_results`
- `canonical_answers`
- `session_completed`
- `submitted_answer`

## Stats

### `GET /api/stats`

Returns stats for the selected scope and active user.

Requires `X-User-Id`.

Supported query params:

- `module_id`
- `review_only`

The response contains:

- `summary`
- `recent_sessions`
- `questions`

Each question row includes:

- current question content
- attempts and accuracy
- `last_asked_at`
- user review flag
- recent aggregated incorrect answers
- derived schedule state

Current schedule fields include:

- `bucket`
- `logical_bucket`
- `recovery_streak`
- `interval_step`
- `last_incorrect_at`
- `next_due_at`
- `retry_pending`

## Questions

### `POST /api/questions`

Creates a new question.

Practical request fields:

- `module_id`
- `prompt`
- `question_type`
- `rank`
- optional `priority_mode` for create flow (`high`, `mid`, `low`)
- `accepted_answers`
- optional `segments`

If `priority_mode` is used, the frontend also sends `X-User-Id` so the backend can place the new question relative to that user's unseen questions.

### `POST /api/questions/{question_id}/revisions`

Updates an existing question in place and can optionally reset history-derived stats.

### `PATCH /api/questions/{question_id}/review-flag`

Sets the current user’s review flag for a question.

Requires `X-User-Id`.

Practical request shape:

```json
{
  "review_flag": true
}
```

## Question Import

Imports are stateless and target one leaf module.

### QML format

Uploads use one question per line in `questions.dsl` / QML syntax.

Important behavior:

- one upload targets one leaf module
- uploads may overlap existing questions
- duplicate prompts are skipped automatically
- malformed lines are returned for repair
- nothing is saved until commit succeeds

Type inference:

- trailing `{...}` = `multi_text`
- trailing `[...]` with commas = `ordered_multi`
- trailing `[...]` without commas = `single_text` or `computed_text`
- embedded `[...]` in the sentence = `inline_cloze`

### `POST /api/question-imports/validate`

Validates pasted QML text or edited unresolved lines.

Returns:

- `ready_to_commit`
- `valid_row_count`
- `skipped_duplicate_count`
- `skipped_rows`
- `unresolved_rows`
- `report_text`

### `POST /api/question-imports/commit`

Commits the current kept rows in one transaction.

The backend revalidates before insert and returns commit counts in the same result shape.
