# Learning App Database

This document describes the conceptual data model.

See also:

- [Overview](overview.md)
- [API](api.md)
- [UI](ui.md)

## Overview

The database is organized around:

- shared study content
- moderation state around shared study content
- user-owned quiz history
- user-owned review state
- authenticated account sessions

The runtime database is PostgreSQL.

## Modules

`modules` stores the content hierarchy.

Each module keeps:

- `parent_id`
- `slug`
- `full_slug`
- `instruction`
- `created_by_user_id`
- `admin_verified`
- `moderation_status`
- `created_at`

Important choices:

- `full_slug` is the stable human-readable path
- display title is derived from `slug`
- only leaf modules may contain questions

## Questions

`questions` stores shared question content.

Each question keeps:

- `module_id`
- `question_type`
- `prompt`
- `prompt_key`
- `rank`
- `type_config_json`
- `created_by_user_id`
- `admin_verified`
- `moderation_status`
- `enabled`
- `replaced_by_question_id`
- `progress_from_question_id`

Important choices:

- new uploaded questions are first-class pending rows until admin verification
- verified question content is shared, but regular-user revisions and delete requests live in proposals
- answered or verified questions are versioned immutably: revisions create a new enabled question and disable the old row
- `replaced_by_question_id` links a disabled row to the replacement that superseded it
- `progress_from_question_id` lets a replacement include prior attempts when stats are intentionally not reset
- `prompt_key` stores the normalized duplicate-matching identity used for indexed question lookups
- ordinary create/revise duplicate checks happen per leaf module through indexed `prompt_key` lookups
- import review can also match same-prompt questions elsewhere in the same top-level module tree through `prompt_key` lookups
- question order is append-only within a leaf; `rank` is the exposed storage field, and sparse gaps are allowed
- import-created and import-relocated questions append at the end of the target leaf

`question_bundles` stores bundle variants for `question_type = "bundle"` questions.

Each bundle variant keeps:

- `question_id`
- `variant_index`
- `prompt_values_json`
- `accepted_answers_json`

Important choices:

- one `questions` row is still the learning item identity for a bundle
- each bundle variant is a row so quiz items and attempts can point to the exact served variant
- export rebuilds canonical bundle QML from ordered variant rows

## Users, Sessions, And Review Flags

`users` stores real authenticated accounts.

Each user keeps:

- `handle`
- `display_name`
- `role`
- `password_hash`
- `created_at`

`auth_sessions` stores server-issued login sessions for real accounts.

`question_revision_proposals` stores regular-user revisions and delete requests against verified shared questions.

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

`quiz_session_items` stores one selected question inside an active or historical quiz session.

Each item keeps:

- `session_id`
- `question_id`
- `bundle_variant_id`
- `score_earned`
- `score_possible`
- `resolved_prompt`
- `resolved_type_config_json`
- `submitted_answer_json`

`attempts` stores the durable answered-history row used by stats and scheduling.

Each attempt keeps:

- `session_id`
- `user_id`
- `question_id`
- `module_id`
- `bundle_variant_id`
- `score_earned`
- `score_possible`
- `submitted_answer_json`
- `answered_at`

Important choices:

- `quiz_session_items` remains the active quiz-session item list and submission guard
- bundle quiz items and attempts store `bundle_variant_id` when a concrete variant was served
- attempts point to the exact question version that was answered
- progress is derived from `attempts`, not cached on questions
- replacement questions can include prior-version attempts by following `progress_from_question_id`
- scheduling is derived from history, not stored in a dedicated schedule table
- `submitted_answer_json` is kept because the revision drawer needs prior incorrect answers

## Derived Scheduling

Scheduling is derived per user from quiz history.

The model separates:

- short-term hotness (`hot0`, `hot1`, `hot1_sit_out`)
- long-term bucket memory (`1h` through `60d`)
- `mastery`

Review-flagged questions are excluded from serving and treated separately in stats.

## Seed Content

Repo seed content imports from `content/modules`.

Behavior:

- module hierarchy is inferred from directory structure
- `module.yaml` is only used for optional `instruction`
- `questions.dsl` is the seed question format

## Relationships

- modules own questions
- users own quiz sessions
- quiz sessions own quiz session items
- users own review flags over shared questions
- users also own auth sessions
- users can own pending modules, pending uploaded questions, and revision proposals

That split keeps the durable model relatively small:

- shared content in `modules` and `questions`
- user study history in `quiz_sessions` and `attempts`
- user maintenance state in `user_review_flags`
