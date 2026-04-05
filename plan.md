# Productionization Plan

## Completed

- multi-user foundation with shared content and user-scoped progress
- forward SQLite migrations instead of reset-on-startup behavior
- user picker and user-scoped quiz, stats, and review flows
- Dockerfile and `docker-compose.yml` for the current SQLite deployment shape
- env-based runtime config for DB path, CORS, and seed-on-boot behavior
- root `README.md` and deployment docs

## Remaining

- move deployed runtime storage from SQLite to PostgreSQL
- introduce a proper migration/deploy workflow for production database changes
- make seed import and other maintenance tasks explicit operator commands rather than relying on app startup
- add backup/restore and release runbook documentation
- add CI checks for backend tests, frontend tests/build, and container smoke validation

## Next

The next concrete phase is the PostgreSQL runtime migration.

That should include:

- choosing the Python database layer for Postgres
- updating the schema/migration strategy for a long-lived production DB
- adapting the app config to `LEARNING_APP_DATABASE_URL` connection-string semantics
- updating Compose to run `app + postgres`

## Assumptions

- shared content remains global
- progress, review state, and spaced-repetition state remain user-owned
- no authentication is added yet
