from __future__ import annotations

import os
import unittest
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql

from backend.app.database import get_connection, initialize_database
from backend.app.main import create_app
from backend.app.services import sync_seed_content
from backend.app.settings import CONTENT_DIR, resolve_database_url


APP_DATABASE_URL = resolve_database_url()


def _database_name(database_url: str) -> str:
    return urlsplit(database_url).path.lstrip("/")


def _replace_database_name(database_url: str, database_name: str) -> str:
    parts = urlsplit(database_url)
    updated = SplitResult(
        scheme=parts.scheme,
        netloc=parts.netloc,
        path=f"/{database_name}",
        query=parts.query,
        fragment=parts.fragment,
    )
    return urlunsplit(updated)


def _derive_test_database_url(app_database_url: str) -> str:
    database_name = _database_name(app_database_url) or "learning"
    test_database_name = database_name if database_name.endswith("_test") else f"{database_name}_test"
    return _replace_database_name(app_database_url, test_database_name)


TEST_DATABASE_URL = os.environ.get("LEARNING_APP_TEST_DATABASE_URL") or _derive_test_database_url(APP_DATABASE_URL)


def validate_test_database_url(test_database_url: str, app_database_url: str) -> None:
    app_database_name = _database_name(app_database_url)
    test_database_name = _database_name(test_database_url)
    if not test_database_name:
        raise RuntimeError("Backend tests require a PostgreSQL database name in the test database URL.")
    if test_database_name == app_database_name:
        raise RuntimeError("Refusing to run backend tests against the normal app database.")
    if not test_database_name.endswith("_test"):
        raise RuntimeError("Refusing to run backend tests against a database that does not end with '_test'.")


def ensure_test_database_exists(test_database_url: str) -> None:
    test_database_name = _database_name(test_database_url)
    admin_database_url = _replace_database_name(test_database_url, "postgres")
    with psycopg.connect(admin_database_url, autocommit=True) as connection:
        row = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (test_database_name,),
        ).fetchone()
        if row is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_database_name))
            )


def reset_test_database(database_url: str) -> None:
    with get_connection(database_url) as connection:
        connection.execute(
            """
            TRUNCATE TABLE
                quiz_session_items,
                quiz_sessions,
                user_review_flags,
                questions,
                modules,
                users
            RESTART IDENTITY CASCADE
            """
        )


class PostgresBackendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        validate_test_database_url(TEST_DATABASE_URL, APP_DATABASE_URL)
        ensure_test_database_exists(TEST_DATABASE_URL)
        initialize_database(TEST_DATABASE_URL)

    def setUp(self) -> None:
        reset_test_database(TEST_DATABASE_URL)
        with get_connection(TEST_DATABASE_URL) as connection:
            sync_seed_content(connection, Path(CONTENT_DIR))
        self.client = TestClient(create_app(database_url=TEST_DATABASE_URL, content_root=CONTENT_DIR))
