# Deployment

## Current Shape

The current container deployment is:

- one `postgres` container
- one `app` container
- built Svelte frontend served by FastAPI
- PostgreSQL stored on a named Docker volume

## Environment Variables

- `LEARNING_APP_PORT`
  Host port published by Docker Compose. Default: `8000`
- `LEARNING_APP_DATABASE_URL`
  PostgreSQL connection string used by the app container.
- `LEARNING_APP_SEED_ON_BOOT`
  When `true`, startup imports any missing seed content from `content/modules`. Default: `true`
- `LEARNING_APP_CORS_ORIGINS`
  Optional comma-separated list of allowed origins when the frontend is served from a different host.
- `LEARNING_APP_ENV`
  Runtime environment label. Compose sets this to `production`.
- `POSTGRES_DB`
  Default database name for the `postgres` container.
- `POSTGRES_USER`
  Default database user for the `postgres` container.
- `POSTGRES_PASSWORD`
  Default database password for the `postgres` container.
- `POSTGRES_PORT`
  Host port published for PostgreSQL. Default: `5432`

## Start

```bash
cp .env.example .env
docker compose up --build
```

The app will listen on `http://127.0.0.1:${LEARNING_APP_PORT:-8000}`.

## Stop

```bash
docker compose down
```

This stops the app but keeps the PostgreSQL volume.

## Reset Local Container Data

```bash
docker compose down -v
```

That removes the `postgres_data` volume and recreates the app state from seed content on the next boot.

## Manual Seed Import

If boot-time seed import is disabled, run:

```bash
docker compose run --rm app python -m backend.app.cli init-db
docker compose run --rm app python -m backend.app.cli import-content
```

## Healthcheck

The Compose service healthcheck calls:

```text
GET /api/health
```

## Notes For The Next Phase

The next productionization step is to add a proper migration/deploy workflow and a Postgres-backed automated test harness.
