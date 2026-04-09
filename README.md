# Learning App

Learning App is a local-first study tool with three main surfaces:

- `Quiz` for active recall
- `Stats` for question performance and revision work
- `Admin` for module management and QML imports

The current runtime target is Docker Compose with:

- FastAPI serving the built Svelte frontend
- PostgreSQL as the only application database

## Runtime

Start the full stack with Docker Compose:

```bash
cp .env.example .env
docker compose up -d --build
```

The app will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

For the published release/install flow, use the separate deploy artifact:

```bash
docker compose -f docker-compose.deploy.yml pull
docker compose -f docker-compose.deploy.yml up -d
```

Release tagging details are in [docs/deployment.md](docs/deployment.md).
Published-image testing details are also in [docs/deployment.md](docs/deployment.md).

## Tests

Frontend:

```bash
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Backend:

```bash
./.venv/bin/python -m py_compile backend/app/database.py backend/app/main.py backend/app/cli.py backend/app/services.py
```

Optional Postgres-backed backend integration tests:

```bash
LEARNING_APP_TEST_DATABASE_URL=postgresql://learning:learning@127.0.0.1:5432/learning_test \
  ./.venv/bin/python -m unittest discover -s tests/backend -v
```

## Runtime Notes

- The default repo-root Compose flow builds from the local working tree.
- The release/install flow uses `docker-compose.deploy.yml` and pulls `ghcr.io/igvw/learning-app`.
- The app image serves the built frontend from FastAPI.
- The app uses PostgreSQL only.
- Seed content is imported on boot by default.
- Set `LEARNING_APP_SEED_ON_BOOT=false` if you want to manage seed import manually.
- Set `LEARNING_APP_CORS_ORIGINS` only when the frontend is hosted on a different origin.

Documentation starts at [docs/overview.md](docs/overview.md).
Supporting docs:

- [docs/api.md](docs/api.md)
- [docs/database.md](docs/database.md)
- [docs/ui.md](docs/ui.md)
- [docs/question-markup.md](docs/question-markup.md)
- [docs/question-markup-llm-prompt.md](docs/question-markup-llm-prompt.md)
- [docs/spaced-repetition.md](docs/spaced-repetition.md)
- [docs/deployment.md](docs/deployment.md)
- [docs/TODO.md](docs/TODO.md)
