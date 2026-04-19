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
- authenticated routes use the server-side session cookie
- `demo` uses the same route surface, but write routes reject with a demo-mode error instead of mutating the real database

## Authentication

### `GET /api/health`

Returns:

- `status`
- `instance_key`
- `bootstrap_required`

### `POST /api/auth/bootstrap-admin`

Creates the first admin account when no admin exists yet, then starts a session.

Practical request shape:

```json
{
  "handle": "admin",
  "display_name": "Admin",
  "password": "password123"
}
```

### `POST /api/auth/login`

Signs in a real account and sets the session cookie.

### `POST /api/auth/logout`

Clears the current session cookie.

### `GET /api/auth/me`

Returns the current authenticated actor:

- `id`
- `handle`
- `display_name`
- `role` (`admin`, `user`, `demo`)
- `is_demo`
- `created_at`

### `POST /api/auth/demo-session`

Starts an ephemeral demo session.

## Modules

### `GET /api/modules/tree`

Returns the visible module tree for the current actor.

Each node includes:

- `id`
- `title`
- `slug`
- `full_slug`
- `instruction`
- `admin_verified`
- `moderation_status`
- `created_by_user_id`
- `creator_display_name`
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

Admin-only. Returns the current real account list.

### `POST /api/users`

Admin-only. Creates one real account.

Practical request shape:

```json
{
  "handle": "ignazio",
  "display_name": "Ignazio",
  "role": "user",
  "password": "password123"
}
```

### `POST /api/users/{user_id}/password`

Admin-only. Replaces one real account password.

### `GET /api/contributions/me`

Returns the current regular user’s pending modules, pending uploaded questions, and revision/delete proposals.

### `GET /api/moderation/queue`

Admin-only. Returns pending module submissions, pending question uploads, and pending question revisions/delete requests.

### `POST /api/moderation/modules/{module_id}`

### `POST /api/moderation/questions/{question_id}`

### `POST /api/moderation/question-revisions/{proposal_id}`

Admin-only moderation actions. Request shape:

```json
{
  "action": "approve",
  "note": ""
}
```

## Quiz Sessions

### `POST /api/quiz-sessions`

Starts a quiz session for the authenticated actor.

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
- verification and provenance fields
- optional viewer proposal state when a personal revision overlay is active
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
- `default_answers`
- `accepted_answer_groups`
- `matched_default_answers`
- `session_completed`
- `submitted_answer`

Current feedback behavior:

- `canonical_answers` remains the compatibility field
- `default_answers` is the first accepted answer for each slot
- `accepted_answer_groups` contains the full accepted answers for each slot in authoring order
- `matched_default_answers` marks whether each submitted slot matched that slot’s first accepted answer

## Stats

### `GET /api/stats`

Returns stats for the selected scope and authenticated actor.

Supported query params:

- `module_id`
- `review_only`

Current frontend behavior note:

- the shipped stats page requests full-scope stats and filters review rows client-side
- `review_only` remains a supported backend query parameter for direct API callers

The response contains:

- `schedule_timezone`
- `summary`
- `recent_sessions`
- `questions`

Each question row includes:

- current question content
- attempts and accuracy
- `first_asked_at`
- `last_asked_at`
- user review flag
- verification and provenance fields
- optional viewer proposal state when the current actor has a personal revision overlay
- recent aggregated incorrect answers
- derived schedule state

Current schedule fields include:

- `bucket`
- `logical_bucket` (`review`, `unseen`, fixed bucket labels from `1h` through `60d`, or `mastery`)
- `recovery_streak`
- `interval_step`
- `last_incorrect_at`
- `next_due_at`

`next_due_at` uses exact elapsed timestamps for `<1d` buckets. For `1d` and above, it is the start of the due calendar day in the configured app schedule timezone.

## Questions

### `POST /api/questions`

Creates a new question.

Current role behavior:

- admins create verified questions immediately
- regular users create pending questions that are immediately usable only for themselves and visible to admins

Practical request fields:

- `module_id`
- `prompt`
- `question_type`
- `rank` (accepted for compatibility; create placement is server-managed append order)
- `accepted_answers`
- optional `segments`

### `POST /api/questions/{question_id}/revisions`

Current role behavior:

- admins update the verified question in place and can optionally reset history-derived stats
- regular users editing a verified question create or update a personal revision proposal instead
- regular users editing their own pending uploaded question update that pending row directly

### `DELETE /api/questions/{question_id}`

Current role behavior:

- admins delete the question immediately
- regular users delete only their own pending uploaded questions immediately
- regular users deleting a verified question create or update a personal delete request proposal instead

### `PATCH /api/questions/{question_id}/review-flag`

Sets the current user’s review flag for a question.

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
- imported creates and same-tree relocations append at the end of the target leaf while preserving batch order
- deletes and source-module moves leave sparse rank gaps; shared order is append-only for now
- malformed or conflicting rows are returned for review
- nothing is saved until commit succeeds
- regular-user imports only create new pending uploaded questions; they do not revise or relocate shared verified questions

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
- the frontend currently uses this endpoint in 50-row chunks to show determinate save progress
- imports can keep running in the current tab after the drawer is hidden; reopening the drawer shows the live remaining state
