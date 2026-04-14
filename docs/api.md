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

### `PATCH /api/modules/{module_id}`

Updates one existing leaf module.

Practical request shape:

```json
{
  "title": "verbs_to_english",
  "instruction": "Translate each Norwegian verb into English."
}
```

Current behavior:

- leaf-module rename keeps the same module id
- only the selected leaf segment is renamed
- parent paths remain unchanged

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
- `first_asked_at`
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

### `DELETE /api/questions/{question_id}`

Deletes one question and closes the rank gap in its leaf module.

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
- repo seed authoring still uses `questions.dsl`, but Admin uploads use pasted QML or `.qml` files
- exact duplicate rows are omitted and summarized
- same-leaf duplicate rows can revise the existing question in place
- same-tree prompt matches can move an existing question into a different leaf while keeping question-linked progress
- malformed or conflicting rows are returned for review
- nothing is saved until commit succeeds

Type inference:

- trailing `{...}` = `multi_text`
- trailing `[...]` with commas = `ordered_multi`
- trailing `[...]` without commas = `single_text` or `computed_text`
- embedded `[...]` in the sentence = `inline_cloze`

### `POST /api/question-imports/validate`

Validates pasted QML text or an edited row list.

Request shape:

```json
{
  "module_id": 12,
  "qml_text": "l\u00f8rdag [Saturday]"
}
```

or:

```json
{
  "module_id": 12,
  "rows": [
    { "row_number": 35, "qml_line": "mot [against|toward]" }
  ]
}
```

Result fields:

- `ready_to_commit`
- `rows`
- `valid_row_count`
- `committable_row_numbers`
- `exact_duplicate_count`
- `review_rows`
- `report_text`
- `committed`
- `committed_count`

Each `review_row` includes:

- `row_number`
- `qml_line`
- `status`
- `status_text`
- `editable`
- `blocking`
- `target_module_full_slug`
- `current_answer_blocks`
- `imported_answer_blocks`
- `matched_questions`

Current review statuses:

- `invalid`
- `duplicate`
- `relocation`
- `info`
- `conflict`

### `POST /api/question-imports/commit`

Commits the submitted row list after revalidation.

Current behavior:

- blocking review rows prevent commit
- exact duplicates commit nothing and report `committed: false`
- successful commits return the same result shape with:
  - `committed: true`
  - `committed_count`
- the frontend currently uses this endpoint in 10-row chunks to show determinate save progress
