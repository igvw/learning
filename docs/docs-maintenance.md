# Docs Maintenance

This document defines the docs structure, ownership boundaries, and editing rules for the docs tree.

## Structure

- `README.md`
  Install-first entry point. Keep it short and high-signal.
- `docs/overview.md`
  Conceptual product map and links to detailed docs.
- `docs/api.md`
  API index. Put detailed route behavior in `docs/api/*.md`.
- `docs/ui.md`
  UI index. Put detailed page and interaction behavior in `docs/ui/*.md`.
- `docs/database.md`
  Data model and persistence concepts.
- `docs/development.md`
  Local development and verification workflow.
- `docs/deployment.md`
  Hosted and container deployment workflow.
- `docs/architecture.md`
  Runtime subsystem map, dependency directions, and guardrails.
- `docs/spaced-repetition.md`
  Scheduler behavior.
- `docs/question-markup.md`
  QML format reference.
- `docs/question-markup-llm-prompt.md`
  Standalone prompt for external LLM use.
- `docs/TODO.md` and `docs/roadmap.md`
  Planning and future work.

## API Docs

Use `docs/api/*.md` for detailed route behavior:

- `auth.md`
- `content.md`
- `study.md`
- `imports.md`

Keep `docs/api.md` as the short index and route-group map.

## UI Docs

Use `docs/ui/*.md` for detailed page and interaction behavior:

- `auth.md`
- `quiz.md`
- `stats.md`
- `manage.md`
- `imports.md`

Keep `docs/ui.md` as the short UI index and shared navigation overview.

## Writing Rules

- Write current-state docs in present tense.
- Remove stale historical comparison language when behavior changes.
- Update the focused doc that owns the behavior instead of duplicating prose across multiple docs.
- Keep operational fallback notes only when they still matter to users or operators.
- Keep edits small and meaningful; do not expand `README.md` when a focused doc is the better home.
