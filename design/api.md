# Learning App API Design

This document describes the current API surface by capability. It is meant to be practical and design-oriented rather than exhaustive.

See also:

- [Overview](overview.md)
- [Database](database.md)
- [UI](ui.md)

## Conventions

- All app routes live under `/api`.
- Payloads are JSON.
- `question_type` is one of `single_text`, `multi_text`, `ordered_multi`, or `inline_cloze`.
- `module_id` is optional on quiz and stats routes at the API layer, although the current UI usually keeps a specific module selected.

## Modules

### `GET /api/modules/tree`

Returns the full module tree as nested nodes.

Each node includes the current module-level fields the UI depends on:

- `id`
- `title`
- `slug`
- `full_slug`
- `instruction`
- `ui_copy`
- `children`

This is the main navigation and authoring source of truth for module structure.

### `POST /api/modules`

Creates one module node.

Practical request shape:

```json
{
  "title": "nouns_to_english",
  "parent_id": 12,
  "instruction": "Translate each Norwegian noun into English.",
  "ui_copy": {
    "question_label": "Question",
    "answer_label": "Answer",
    "stats_title": "Stats",
    "review_title": "Review"
  }
}
```

Important behavior:

- the backend creates one node at a time
- the current frontend builds `mkdir -p` behavior by making repeated module-create calls for slash-separated paths
- child modules can only be added under parents that are still valid module containers for direct questions

## Quiz Sessions

### `POST /api/quiz-sessions`

Starts a quiz session for a selected module scope.

Practical request shape:

```json
{
  "module_id": 12,
  "count": 10
}
```

Practical response shape:

- session `id`
- selected `module_id`
- optional `completed_at`
- `items[]`

Each item includes the current quiz-facing fields the UI needs:

- question and module identifiers
- module title and module instruction
- prompt and question type
- rank
- normalized `type_config`
- current answer state fields such as `submitted_answer`, `is_correct`, `score_earned`, and `score_possible`

### `POST /api/quiz-sessions/{session_id}/items/{item_id}/submit`

Submits answers for one question inside a session.

Practical request shape:

```json
{
  "answers": ["white nile", "blue nile"]
}
```

Practical response shape:

- `item_id`
- `is_correct`
- `score_earned`
- `score_possible`
- `slot_results`
- `canonical_answers`
- `session_completed`
- `submitted_answer`

This is the route that powers per-question grading, fractional credit, and the transition into the completed-session state.

## Stats

### `GET /api/stats`

Returns stats for the selected module scope.

Supported query params:

- `module_id`
- `review_only`

The response is grouped into:

- `summary`
- `recent_sessions`
- `questions`

Important behavior:

- recent-session data reflects the latest sessions whose `quiz_sessions.module_id` matches the selected module
- question rows include the current editable question content plus derived stats like attempts, accuracy, and last asked time
- review state is still returned per question even though the current UI now renders it as row treatment instead of a separate column

## Questions

### `POST /api/questions`

Creates a new question in the current shared-content model.

Practical request fields:

- `module_id`
- `prompt`
- `question_type`
- `rank`
- `review_flag`
- `accepted_answers`
- optional `slot_prompts`
- optional `segments`

### `POST /api/questions/{question_id}/revisions`

Updates an existing question and can optionally reset derived stats.

The route name still reflects the older revision model, but the current implementation updates the current question record rather than storing a separate version-history table.

### `PATCH /api/questions/{question_id}/review-flag`

Toggles the current question review flag.

Practical request shape:

```json
{
  "review_flag": true
}
```

## Question Import Sessions

The import flow is a staged upload workflow rather than a one-shot bulk-create endpoint.

### CSV format

Uploads use a universal CSV with the exact header:

```text
prompt,answers
```

Important rules:

- one upload session targets one leaf module
- one CSV may mix question types
- multiline CSV fields are rejected
- initial `rank` comes from the original data-row number

Type inference rules:

- `inline_cloze`: `prompt` contains `[answer | alternate]` blanks and `answers` is empty
- `ordered_multi`: `answers` starts with `ordered:`
- `multi_text`: `answers` contains `;` groups and does not start with `ordered:`
- `single_text`: everything else

### `POST /api/question-import-sessions`

Creates an import session and validates the uploaded CSV text.

Practical request shape:

```json
{
  "module_id": 12,
  "csv_text": "prompt,answers\nhund,dog"
}
```

Practical response shape:

- `session_id`
- `expires_at`
- `ready_to_commit`
- `staged_valid_count`
- `unresolved_rows`
- `report_text`

Each unresolved row includes:

- `row_number`
- `csv_line`
- `issues`
- optional `inferred_type`

### `POST /api/question-import-sessions/{session_id}/revalidate`

Revalidates the currently unresolved rows after the user edits them in the client.

Request shape:

```json
{
  "rows": [
    {
      "row_number": 3,
      "csv_line": "run,ordered: run ; ran ; run"
    }
  ]
}
```

### `DELETE /api/question-import-sessions/{session_id}/rows/{row_number}`

Discards one unresolved row from the pending import session.

### `POST /api/question-import-sessions/{session_id}/commit`

Attempts to commit all staged valid rows.

Important behavior:

- the server rechecks conflicts before commit
- if unresolved or newly conflicting rows remain, nothing is saved
- on success, all staged rows are created atomically and the import session is marked committed

This staged API shape is what allows the current line-numbered repair flow in the UI.
