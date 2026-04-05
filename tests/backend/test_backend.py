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
                question_import_session_rows,
                question_import_sessions,
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
class PostgresBackendIntegrationTests(unittest.TestCase):
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

    def test_users_can_be_created_and_listed(self) -> None:
        create_response = self.client.post(
            "/api/users",
            json={"handle": "alice", "display_name": "Alice"},
        )
        self.assertEqual(create_response.status_code, 200)

        list_response = self.client.get("/api/users")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            list_response.json(),
            [
                {
                    "id": 1,
                    "handle": "alice",
                    "display_name": "Alice",
                    "created_at": create_response.json()["created_at"],
                    "disabled_at": None,
                }
            ],
        )

    def test_quiz_flow_is_user_scoped(self) -> None:
        user = self.client.post(
            "/api/users",
            json={"handle": "alice", "display_name": "Alice"},
        ).json()

        unauthenticated = self.client.post(
            "/api/quiz-sessions",
            json={"module_id": 5, "count": 2},
        )
        self.assertEqual(unauthenticated.status_code, 400)

        session_response = self.client.post(
            "/api/quiz-sessions",
            json={"module_id": 5, "count": 2},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(session_response.status_code, 200)
        session = session_response.json()
        self.assertEqual(session["module_id"], 5)
        self.assertEqual(len(session["items"]), 2)

        first_item = session["items"][0]
        submit_response = self.client.post(
            f"/api/quiz-sessions/{session['id']}/items/{first_item['id']}/submit",
            json={"answers": ["nairobi"]},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.json()["score_possible"], 1.0)

        stats_response = self.client.get(
            "/api/stats",
            params={"module_id": 5},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(stats_response.status_code, 200)
        self.assertGreaterEqual(stats_response.json()["summary"]["total_attempts"], 1)
