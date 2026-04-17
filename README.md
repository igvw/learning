# Learning App

Learning App is a local-first study tool with three main surfaces:

- `Quiz` for active recall
- `Stats` for question performance, revision, and delete work
- `Admin` for module management, users, and QML imports

## Install

Canonical install uses the published image and the repo's deploy Compose file.

1. Copy the env template and adjust credentials if you do not want the defaults:

```bash
cp .env.example .env
```

Default first-admin sign-in from `.env.example`:

- handle: `admin`
- password: `password123`

2. Start the stack:

```bash
docker compose -f docker-compose.deploy.yml pull
docker compose -f docker-compose.deploy.yml up -d
```

The app will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000) with the sample `.env`.

## `docker-compose.deploy.yml`

```yaml
services:
  postgres:
    image: postgres:16-bookworm
    environment:
      POSTGRES_DB: ${POSTGRES_DB:?Set POSTGRES_DB in .env}
      POSTGRES_USER: ${POSTGRES_USER:?Set POSTGRES_USER in .env}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
    ports:
      - "${POSTGRES_PORT:?Set POSTGRES_PORT in .env}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 10s
    restart: unless-stopped

  app:
    image: ${LEARNING_APP_IMAGE:?Set LEARNING_APP_IMAGE in .env}
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      LEARNING_APP_ENV: ${LEARNING_APP_ENV:?Set LEARNING_APP_ENV in .env}
      LEARNING_APP_INSTANCE_KEY: ${LEARNING_APP_INSTANCE_KEY:?Set LEARNING_APP_INSTANCE_KEY in .env}
      LEARNING_APP_DATABASE_URL: postgresql://${POSTGRES_USER:?Set POSTGRES_USER in .env}:${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}@postgres:5432/${POSTGRES_DB:?Set POSTGRES_DB in .env}
      LEARNING_APP_SEED_ON_BOOT: ${LEARNING_APP_SEED_ON_BOOT:?Set LEARNING_APP_SEED_ON_BOOT in .env}
      LEARNING_APP_CORS_ORIGINS: ${LEARNING_APP_CORS_ORIGINS:-}
      LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE: ${LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE-}
      LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME: ${LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME-}
      LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD: ${LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD-}
    ports:
      - "${LEARNING_APP_PORT:?Set LEARNING_APP_PORT in .env}:8000"
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).read()",
        ]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 10s
    restart: unless-stopped

volumes:
  postgres_data:
```

## Source Build

To build from the local working tree instead of the published image:

```bash
cp .env.example .env
docker compose up -d --build
```

## Tests

Frontend:

```bash
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Backend local dev and test setup is documented in [docs/development.md](docs/development.md).
Deployment details, backup flow, and published-image notes are in [docs/deployment.md](docs/deployment.md).
Documentation starts at [docs/overview.md](docs/overview.md).
