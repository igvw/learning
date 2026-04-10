# Development

## Local Backend Tests

Normal backend tests should run locally, not through Docker.

Use a local Python 3.14 environment, then install backend dependencies:

```bash
python3.14 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r backend/requirements.txt
```

Compile the backend modules:

```bash
./.venv/bin/python -m py_compile backend/app/database.py backend/app/main.py backend/app/cli.py backend/app/services.py backend/app/service/*.py
```

Run backend tests:

```bash
./.venv/bin/python -m unittest discover -s tests/backend -v
```

By default, the Postgres-backed integration tests derive a sibling test database from `LEARNING_APP_DATABASE_URL`. For the normal local setup, that means the app can keep using `learning` while tests automatically use `learning_test` on the same PostgreSQL server.

The test database is created automatically if needed, and the test suite truncates only that `*_test` database. It does not touch the normal app database.

If you need a different test database, override it explicitly:

```bash
LEARNING_APP_TEST_DATABASE_URL=postgresql://learning:learning@127.0.0.1:5432/learning_test \
  ./.venv/bin/python -m unittest discover -s tests/backend -v
```
