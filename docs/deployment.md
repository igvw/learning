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

- `POSTGRES_DB`
  Database name for the `postgres` container. Required in `.env`.
- `POSTGRES_USER`
  Database user for the `postgres` container. Required in `.env`.
- `POSTGRES_PASSWORD`
  Database password for the `postgres` container. Required in `.env`.
- `POSTGRES_PORT`
  Host port published for PostgreSQL. Sample `.env.example` value: `5432`.
- `LEARNING_APP_PORT`
  Host port published by Docker Compose. Sample `.env.example` value: `8000`.
- `LEARNING_APP_IMAGE`
  Published GHCR image used by the app service. Sample `.env.example` value: `ghcr.io/igvw/learning-app:latest`.
- `LEARNING_APP_ENV`
  Runtime environment label. Sample `.env.example` value: `production`.
- `LEARNING_APP_INSTANCE_KEY`
  Browser storage namespace and health metadata key. Sample `.env.example` value: `published`.
- `LEARNING_APP_SEED_ON_BOOT`
  When `true`, startup imports any missing seed content from `content/modules`. Sample `.env.example` value: `true`.
- `LEARNING_APP_CORS_ORIGINS`
  Optional comma-separated list of allowed origins when the frontend is served from a different host.
- `LEARNING_APP_SCHEDULE_TIMEZONE`
  App-wide timezone used for day-scale spaced-repetition buckets and day-based stats graphs. When unset, the backend defaults to `UTC`. Hosted deployments can set this to something like `Europe/Oslo`.
- `LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE`
  Optional first-admin handle. When all three bootstrap admin vars are present and no admin exists yet, startup creates that first admin automatically.
- `LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME`
  Optional first-admin display name used by env bootstrap.
- `LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD`
  Optional first-admin password used by env bootstrap.
- `LEARNING_APP_DATABASE_URL`
  Optional full PostgreSQL connection string. When unset, the backend can build a local connection URL from `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

## Local Development

Use the repo-root Compose file while developing from source:

```bash
cp .env.example .env
docker compose up -d --build
```

This is the standard workflow inside a cloned repo.

## Test The Published Image Safely

To validate the published GHCR image without touching the normal `learning` Compose data, use the helper script from the repo root:

```bash
bash ./tests/published.sh up
```

This test flow is safe because:

- the normal local `learning` stack is only stopped, not removed
- the published-image test runs under a separate Compose project name: `learning-published`
- that separate project gets its own containers, network, and PostgreSQL volume
- the script pulls the latest published image before starting the test stack

When you are done testing:

```bash
bash ./tests/published.sh down
docker compose up -d
```

The `down` command removes only the isolated `learning-published_*` resources, including its test database volume.

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
- published tags are intended to work on both `amd64` and `arm64` hosts, including Apple Silicon, ARM64 VPS machines, and 64-bit Raspberry Pi systems
- branch pushes do not publish images
- the tag workflow runs backend tests, frontend tests, and a frontend build before publishing

## Release Tagging

When you want to publish a new image, tag the current `HEAD` on `main`:

```bash
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Pushing the tag starts the release workflow. It runs the verification checks first, then publishes:

- `ghcr.io/igvw/learning-app:v1.0.0`
- `ghcr.io/igvw/learning-app:latest`

First install:

```bash
cp .env.example .env
docker compose -f docker-compose.deploy.yml pull
docker compose -f docker-compose.deploy.yml up -d
```

With the sample `.env`, the app listens on `http://127.0.0.1:8000`.

The sample `.env.example` also boots the first admin automatically:

- handle: `admin`
- password: `password123`

If you intentionally clear the bootstrap admin vars before first startup, the app still starts and the auth screen falls back to the manual first-admin bootstrap flow.

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
