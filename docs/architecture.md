# Architecture

This document defines the current subsystem map, dependency directions, and the main ownership boundaries for the repo.

## Subsystems

### Backend

- `backend/app/main.py`
  - app factory, middleware, lifespan, and static frontend mounting only
- `backend/app/api/**`
  - HTTP-layer dependencies and route modules
- `backend/app/services.py`
  - public backend service surface for entrypoints
- `backend/app/service/**`
  - domain logic and cohesive shared helpers
- `backend/app/database.py`
  - connection management, schema initialization, and DB utility helpers
- `backend/app/schemas.py`
  - current shared API/data models

### Frontend

- `frontend/src/App.svelte`
  - auth/session/route composition
- `frontend/src/components/**`
  - route and UI components
- `frontend/src/lib/**`
  - browser-side domain logic, persistence helpers, graph builders, import logic, and typed API client
- `frontend/src/styles/**`
  - concern-scoped stylesheets
- `frontend/src/app.css`
  - shared base/layout styles only

### Tests

- `tests/backend/**`
  - backend integration/unit coverage
- `frontend/tests/**`
  - frontend integration/component coverage

## Dependency Directions

Backend:

- `main.py` -> `api/**` -> `services.py` -> `service/**` -> `database.py`
- Route modules must not import `backend.app.service.*` directly.
- Shared helpers inside `service/**` should be imported directly only by other service modules.

Frontend:

- `App.svelte` -> route/components -> `lib/**`
- Components may import child `.svelte` components.
- Shared non-visual logic should live in `lib/**`, not under `components/**`.

Docs and tests:

- Docs describe behavior owned by runtime code; they do not become the runtime source of truth.
- Tests should mirror the same domain boundaries as runtime code where practical.

## Single Source Of Truth

- backend service surface: `backend/app/services.py`
- backend HTTP wiring: `backend/app/api/**`
- backend persistence rules: `backend/app/database.py` and SQL schema files
- frontend API contract usage: `frontend/src/lib/api.ts`
- frontend shared types: `frontend/src/lib/types.ts`
- import/QML runtime logic: `backend/app/qml.py`, `backend/app/service/imports.py`, `backend/app/service/bundles.py`, `frontend/src/lib/import-*.ts`
- QML parser contracts: `tests/fixtures/qml-contracts.json`
- bundle storage/runtime: `questions.question_type = "bundle"` plus `question_bundles`, materialized through `backend/app/service/bundles.py` and `backend/app/service/questions.py`
- answered study history: `attempts`, read by `backend/app/service/schedule.py` and `backend/app/service/stats.py`
- stats graph shaping: `frontend/src/lib/stats/*`
- external QML prompt snippets: `docs/question-markup-prompts/`

## Guardrails

- Avoid new generic helper files such as `utils.ts`, `helpers.ts`, or `common.py`.
- Keep shared helpers medium-grain: one theme, one audience.
- New runtime files should stay below roughly 300-400 lines unless there is a strong reason.
- New test files should stay below roughly 300 lines unless they are intentionally integration-heavy.
- Extend an existing domain module before inventing a new architectural layer.
