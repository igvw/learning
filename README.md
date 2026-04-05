# Learning App

Learning App is a local-first study tool with three main surfaces:

- `Quiz` for active recall
- `Stats` for question performance and revision work
- `Admin` for module management and CSV imports

The current runtime target is Docker Compose with:

- FastAPI serving the built Svelte frontend
- PostgreSQL as the only application database

## Runtime

Start the full stack with Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

The app will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

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

- The app image serves the built frontend from FastAPI.
- The app uses PostgreSQL only.
- Seed content is imported on boot by default.
- Set `LEARNING_APP_SEED_ON_BOOT=false` if you want to manage seed import manually.
- Set `LEARNING_APP_CORS_ORIGINS` only when the frontend is hosted on a different origin.

More operational detail lives in [docs/deployment.md](docs/deployment.md).
