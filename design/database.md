# Learning App Database Design

This document describes the current conceptual data model. It focuses on why data is stored the way it is, not on reproducing raw SQL.

See also:

- [Overview](overview.md)
- [API](api.md)
- [UI](ui.md)

## Overview

The current database is organized around three concerns:

- shared content that defines what can be studied
- quiz history that drives derived stats and progress
- staged import state for CSV uploads that are not ready to commit yet

The current implementation uses SQLite, but the structure is intentionally simple enough to evolve later.

## Modules

`modules` stores the content hierarchy.

Each module represents one node in the study tree and carries:

- parent-child hierarchy
- a local `slug` plus a unique `full_slug`
- a human title
- optional `instruction` text
- lightweight `ui_copy`
- optional `source_id` when content originated from seed files

Important design choices:

- modules are the main scoping unit for quizzes and stats
- a leaf module can hold concise prompts because `instruction` supplies shared context
- parent modules act as bundled study scopes over their descendants

## Questions

`questions` stores the current shared question content.

Each question carries:

- owning `module_id`
- `question_type`
- `prompt`
- `rank`
- `type_config`
- `review_flag`
- optional `source_id`

Important design choices:

- the app keeps only the current question state in this table
- question content is shared content, not user-specific state
- the current schema does not keep a separate version-history table
- duplicate prompt checks happen within a leaf module only, using normalized prompt comparison in app logic rather than a raw SQL uniqueness constraint

## Quiz Sessions

`quiz_sessions` and `quiz_session_items` store quiz history.

`quiz_sessions` records one quiz run at a selected module scope, including:

- the selected `module_id`
- `created_at`
- `completed_at`

`quiz_session_items` stores only the minimal per-question result needed for progress:

- `session_id`
- `question_id`
- `score_earned`
- `score_possible`

Important design choices:

- progress and aggregate stats are derived from quiz history, not cached on questions
- post-quiz review lives in UI state during the active session, not as a persisted snapshot table
- keeping session items minimal makes it easier to add future per-user progress without coupling it to shared question content

## Import Sessions

CSV uploads use staging tables instead of writing directly into `questions`.

`question_import_sessions` represents one short-lived upload session for one target module. It carries:

- the target `module_id`
- creation time
- expiry time
- optional commit time

`question_import_session_rows` stores the row-by-row state inside that session:

- original `row_number`
- raw `csv_line`
- `status`
- optional inferred question type
- optional parsed payload for rows that validated successfully
- validation issues for unresolved rows

Important design choices:

- uploads target one leaf module at a time
- valid rows can be staged while unresolved rows remain editable
- nothing is written to `questions` until commit succeeds
- commit stays atomic so malformed or newly conflicting rows do not create partial imports
- row numbers preserve the original import order, which becomes the initial `rank`

## Relationships And Responsibilities

- modules own questions
- quiz sessions reference the selected study scope
- quiz session items reference the questions that were answered
- import sessions reference a target module and stage candidate questions before they become real questions

This separation keeps the current model easy to reason about:

- shared content lives in `modules` and `questions`
- progress lives in quiz history
- unfinished upload work lives in import-session tables

That division is the main reason the current schema stays relatively flat while still supporting quiz flow, stats, and staged administration.
