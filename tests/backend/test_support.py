from __future__ import annotations

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.database import get_connection, initialize_database
from backend.app.main import create_app
from backend.app.services import sync_seed_content
from backend.app.settings import CONTENT_DIR


TEST_DATABASE_URL = os.environ.get("LEARNING_APP_TEST_DATABASE_URL")


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


@unittest.skipUnless(
    TEST_DATABASE_URL,
    "Set LEARNING_APP_TEST_DATABASE_URL to run Postgres-backed backend integration tests.",
)
class PostgresBackendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert TEST_DATABASE_URL is not None
        initialize_database(TEST_DATABASE_URL)

    def setUp(self) -> None:
        assert TEST_DATABASE_URL is not None
        reset_test_database(TEST_DATABASE_URL)
        with get_connection(TEST_DATABASE_URL) as connection:
            sync_seed_content(connection, Path(CONTENT_DIR))
        self.client = TestClient(create_app(database_url=TEST_DATABASE_URL, content_root=CONTENT_DIR))
