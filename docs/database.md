# Learning App Database

This document describes the current conceptual data model.

See also:

- [Overview](overview.md)
- [API](api.md)
- [UI](ui.md)

## Overview

The database is organized around:

- shared study content
- user-owned quiz history
- user-owned review state

The current runtime database is PostgreSQL.

## Modules

`modules` stores the content hierarchy.

Each module keeps:

- `parent_id`
- `slug`
- `full_slug`
- `instruction`
- `created_at`

Important choices:

- `full_slug` is the stable human-readable path
- display title is derived from `slug`
- only leaf modules may contain questions

## Questions

`questions` stores the current shared question content.

Each question keeps:

- `module_id`
- `question_type`
- `prompt`
- `rank`
- `type_config_json`

Important choices:

- only current question state is stored
- question content is shared, not user-specific
- ordinary create/revise duplicate checks happen per leaf module in app logic
- import review can also match same-prompt questions elsewhere in the same top-level module tree

## Users And Review Flags

`users` stores the study users.

Each user keeps:

- `handle`
- `display_name`
- `created_at`

`user_review_flags` stores user-specific review state keyed by `(user_id, question_id)`.

Important choices:

- review flags are personal, not shared question metadata
- shared content stays separate from user maintenance state

## Quiz History

`quiz_sessions` stores one quiz run.

Each session keeps:

- `user_id`
- `module_id`
- `created_at`
- `completed_at`

`quiz_session_items` stores one answered question inside a session.

Each item keeps:

- `session_id`
- `question_id`
- `score_earned`
- `score_possible`
- `resolved_prompt`
- `resolved_type_config_json`
- `submitted_answer_json`

Important choices:

- progress is derived from quiz history, not cached on questions
- scheduling is derived from history, not stored in a dedicated schedule table
- `submitted_answer_json` is kept because the revision drawer needs prior incorrect answers

## Derived Scheduling

Scheduling is derived per user from quiz history.

The current model separates:

- short-term hotness (`hot0`, `hot1`, `hot1_sit_out`)
- long-term bucket memory (`1h` through `14d`)
- `mastery`

Review-flagged questions are excluded from serving and treated separately in stats.

## Seed Content

Repo seed content still imports from `content/modules`.

Current behavior:

- module hierarchy is inferred from directory structure
- `module.yaml` is only used for optional `instruction`
- `questions.dsl` is the current seed question format

## Relationships

- modules own questions
- users own quiz sessions
- quiz sessions own quiz session items
- users own review flags over shared questions

That split keeps the durable model relatively small:

- shared content in `modules` and `questions`
- user study history in `quiz_sessions` and `quiz_session_items`
- user maintenance state in `user_review_flags`
