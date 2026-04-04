# Flask Learning App

## Summary
- The app is a single-user Flask + SQLite learning app with server-rendered Jinja templates and a small vanilla JavaScript layer for keyboard-first quiz flow.
- The app keeps logic independent from learning content by seeding initial data from `./modules/**/module.yaml` and `./modules/**/questions.csv` into SQLite, then reading and editing only the database at runtime.
- The app supports two v1 question types: `free_text_any` and `free_text_all`.
- The quiz landing page is the default route, and primary navigation is limited to `Quiz`, `Stats`, and a hamburger module menu.

## Core Decisions
- SQLite access uses `sqlite3` plus thin repository and service helpers instead of an ORM.
- Module metadata lives in a simple YAML file, and questions live in CSV with pipe-delimited accepted answers.
- Module slugs are inferred from titles using lowercase and underscores.
- Question identity is split between an internal row id, a stable global `question_code`, and a human-readable `public_id` like `biology-q0001-v2`.
- Rank is a simple numeric importance value such as `1`, `2`, or `2.5`. It is not unique and is not hierarchical.
- Automatic rank suggestions are scoped to the top-level module bundle so submodules share one rough importance scale.
- Free-text grading uses normalized exact matching with multiple accepted answers.
- Stats aggregate by `stats_group_id` so revised questions can either inherit prior performance or start fresh.

## Data Model
- `modules`: adjacency-list hierarchy with `parent_id`, inferred slug, `full_slug`, title, source path, and sort order.
- `module_metadata`: per-module labels for question, answer, stats, and review surfaces plus `extra_json`.
- `questions`: question versions with type, prompt, non-unique numeric rank, active flag, revision lineage, global `question_code`, `public_id`, and `stats_group_id`.
- `question_answers`: one accepted answer per row, including normalized value and display order.
- `sessions`: quiz session metadata including selected module, limit, start and end timestamps, and duration.
- `session_questions`: ordered asked-question rows with prompt and answer snapshots, submission data, correctness, and score contribution.
- `revision_flags`: open or resolved revision requests created from review and stats actions.

## Content Format
- Each module directory contains:
  - `module.yaml`
  - `questions.csv`
- `module.yaml` stays intentionally flat and simple:
  - `title`
  - `sort_order`
  - optional labels such as `question_title`, `answer_label`, `stats_title`, `review_title`
- `questions.csv` uses:
  - `rank`
  - `question_type`
  - `prompt`
  - `accepted_answers`
- `accepted_answers` are pipe-delimited inside the CSV row.

## Routes
- `/` redirects to `/quiz`.
- `/quiz` is the default landing page and quiz launcher for the selected module subtree.
- `/quiz/start` creates a session for the current module selection.
- `/quiz/<session_id>` renders a vertically progressing quiz page.
- `/quiz/<session_id>/answer/<position>` is a JSON submission endpoint used by the keyboard-first quiz UI.
- `/review/<session_id>` shows the session summary and revision flag actions.
- `/stats` shows the performance graph, flagged-question list, and question table for the selected module subtree.
- `/questions/new` is the question creation page and is reached from the floating plus button on stats.
- `/questions/<public_id>/revise` is the editable revision page, including module reassignment.
- `/questions/<public_id>/history` is the read-only history page using the same presentation.

## Ranking And Revisions
- Rank is a numeric importance hint, not a chapter or section path.
- Rank can repeat across questions and across submodules.
- Rank-only edits update the existing row in place and keep the same `public_id`.
- Content or module changes create a new active question version, disable the old row, preserve `question_code`, and increment the version suffix in `public_id`.
- Moving a question to another module happens through the revision form.
- “Invalidate stats” is enabled by default. When checked, the revised question gets a new `stats_group_id`; when unchecked, it reuses the old group.

## UX Notes
- The UI uses a dark grey theme with a persistent header and an off-canvas hamburger menu for module selection.
- The header exposes only two main links: `Quiz` and `Stats`.
- The quiz is the default landing page and focuses on launching or continuing keyboard-first study.
- The create page is not linked from the header and is reached from the floating plus button on the stats page.
- The question create and revise pages show the module hierarchy directly instead of hiding it in a plain dropdown.
- The quiz flow stays keyboard-first:
  - `Enter` submits `free_text_any`
  - `Ctrl+Enter` submits `free_text_all`
  - focus moves to the next card automatically
- Immediate feedback shows green and red question cards, highlights submitted rows, and lists correct or missing answers.
- Stats highlights flagged questions in orange and surfaces flagged items at the top of the page.

## Test Plan
- Unit tests cover normalization, grading, non-unique rank behavior, revision and versioning, module reassignment, and seeding.
- Flask integration tests cover quiz landing, stats, quiz flow, review, creation, and revision-flag flows.
- A manual keyboard acceptance pass covers the full no-mouse quiz and revision workflow after dependencies are installed and the app is runnable.
