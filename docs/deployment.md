# Deployment

## Current Shape

The current container deployment is:

- one `postgres` container
- one `app` container
- built Svelte frontend served by FastAPI
- PostgreSQL stored on a named Docker volume
- local/dev Compose builds from the repo
- deploy Compose pulls the published GHCR image

## Environment Variables

- `LEARNING_APP_PORT`
  Host port published by Docker Compose. Default: `8000`
- `LEARNING_APP_IMAGE`
  Published GHCR image used by the app service. Default: `ghcr.io/igvw/learning-app:latest`
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

## Local Development

Use the repo-root Compose file while developing from source:

```bash
cp .env.example .env
docker compose up -d --build
```

This is the standard workflow inside a cloned repo.

## Install For Another User

This is the laptop-first flow for someone who just wants to study locally.

Prerequisite:

- Docker Desktop installed once while online
- no registry login is needed because the GHCR image is public

Published image policy:

- only manual version tags such as `v1.2.3` publish images
- each tagged release publishes:
  - `ghcr.io/igvw/learning-app:v1.2.3`
  - `ghcr.io/igvw/learning-app:latest`
- branch pushes do not publish images
- the tag workflow runs backend tests, frontend tests, and a frontend build before publishing

First install:

```bash
cp .env.example .env
docker compose -f docker-compose.deploy.yml pull
docker compose -f docker-compose.deploy.yml up -d
```

The app will listen on `http://127.0.0.1:${LEARNING_APP_PORT:-8000}`.

What this means for offline use:

- the first `docker compose pull` needs internet access
- later updates need internet access
- normal study sessions do not need internet once the images are present locally

## Restart After A Reboot

```bash
docker compose -f docker-compose.deploy.yml up -d
```

If the images are already present locally, this works offline.

## Stop

```bash
docker compose -f docker-compose.deploy.yml down
```

This stops the app but keeps the PostgreSQL volume.

## Reset Local Container Data

```bash
docker compose -f docker-compose.deploy.yml down -v
```

That removes the `postgres_data` volume and recreates the app state from seed content on the next boot.

## Manual Seed Import

If boot-time seed import is disabled, run:

```bash
docker compose -f docker-compose.deploy.yml run --rm app python -m backend.app.cli init-db
docker compose -f docker-compose.deploy.yml run --rm app python -m backend.app.cli import-content
```

## Healthcheck

The Compose service healthcheck calls:

```text
GET /api/health
```

## Update To A Newer Version

When a newer image has been published:

```bash
docker compose -f docker-compose.deploy.yml pull app
docker compose -f docker-compose.deploy.yml up -d
```

This recreates the app container while keeping the PostgreSQL volume.

## Data Location And Backup

Study data lives in the named Docker volume `postgres_data`.

What to back up:

- the PostgreSQL data volume, or
- a SQL dump of the running database

Example SQL backup:

```bash
docker compose -f docker-compose.deploy.yml exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > learning-backup.sql
```

Example restore into a fresh stack:

```bash
cat learning-backup.sql | docker compose -f docker-compose.deploy.yml exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

## Notes For The Next Phase

The next productionization step is to add a proper migration/deploy workflow and a Postgres-backed automated test harness.
