import os
import unittest
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql

from backend.app.database import get_connection, initialize_database
from backend.app.main import create_app
from backend.app.schemas import QuestionDraftIn
from backend.app.services import create_module, create_question, sync_seed_content
from backend.app.settings import auth_cookie_name
from backend.app.settings import CONTENT_DIR, resolve_database_url


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


def _derive_app_database_url(test_database_url: str) -> str:
    database_name = _database_name(test_database_url)
    app_database_name = database_name.removesuffix("_test") or database_name
    return _replace_database_name(test_database_url, app_database_name)


def _resolve_backend_test_database_urls() -> tuple[str, str]:
    explicit_test_database_url = (os.environ.get("LEARNING_APP_TEST_DATABASE_URL") or "").strip()
    if explicit_test_database_url:
        return _derive_app_database_url(explicit_test_database_url), explicit_test_database_url

    app_database_url = resolve_database_url()
    return app_database_url, _derive_test_database_url(app_database_url)


APP_DATABASE_URL, TEST_DATABASE_URL = _resolve_backend_test_database_urls()


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
                question_revision_proposals,
                auth_sessions,
                attempts,
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
        self.database_url = TEST_DATABASE_URL
        self.client = TestClient(create_app(database_url=TEST_DATABASE_URL, content_root=CONTENT_DIR))
        self._user_auth_headers: dict[int, dict[str, str]] = {}
        bootstrap_response = self.client.post(
            "/api/auth/bootstrap-admin",
            json={"handle": "admin", "display_name": "Admin", "password": "password123"},
        )
        self.assertEqual(bootstrap_response.status_code, 200)
        self.admin_user = bootstrap_response.json()
        self.admin_headers = self._cookie_headers_from_response(bootstrap_response)
        self.client.cookies.clear()

    def _cookie_headers_from_response(self, response) -> dict[str, str]:
        token = response.cookies.get(auth_cookie_name())
        return {"Cookie": f"{auth_cookie_name()}={token}"} if token else {}

    def create_user(
        self,
        handle: str = "alice",
        display_name: str = "Alice",
        *,
        role: str = "user",
        password: str = "password123",
    ) -> dict[str, object]:
        response = self.client.post(
            "/api/users",
            json={"handle": handle, "display_name": display_name, "role": role, "password": password},
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        created = response.json()
        login_response = self.client.post(
            "/api/auth/login",
            json={"handle": handle, "password": password},
        )
        self.assertEqual(login_response.status_code, 200)
        self._user_auth_headers[int(created["id"])] = self._cookie_headers_from_response(login_response)
        self.client.cookies.clear()
        return created

    def user_headers(self, user_id: int) -> dict[str, str]:
        return self._user_auth_headers[user_id]

    def create_module_record(
        self,
        title: str,
        parent_id: int | None = None,
        instruction: str = "",
    ) -> dict[str, object]:
        with get_connection(self.database_url) as connection:
            return create_module(connection, title=title, parent_id=parent_id, instruction=instruction)

    def create_question_record(
        self,
        module_id: int,
        prompt: str,
        accepted_answers: list[list[str]],
        *,
        question_type: str = "single_text",
        rank: int = 1,
        segments: list[str] | None = None,
        bundle_qml: str | None = None,
    ) -> dict[str, object]:
        with get_connection(self.database_url) as connection:
            return create_question(
                connection,
                QuestionDraftIn(
                    module_id=module_id,
                    prompt=prompt,
                    question_type=question_type,
                    rank=rank,
                    accepted_answers=accepted_answers,
                    segments=segments or [],
                    bundle_qml=bundle_qml,
                ),
                actor=None,
            )

    def create_module_tree(self) -> dict[str, int]:
        norwegian = self.create_module_record("Norwegian")
        vocabulary = self.create_module_record("Vocabulary", norwegian["id"])
        source_a = self.create_module_record("Source A", vocabulary["id"])
        source_b = self.create_module_record("Source B", vocabulary["id"])
        target = self.create_module_record("Target", vocabulary["id"])
        return {
            "norwegian": norwegian["id"],
            "vocabulary": vocabulary["id"],
            "source_a": source_a["id"],
            "source_b": source_b["id"],
            "target": target["id"],
        }

    def start_quiz_session(self, user_id: int, module_id: int | None, count: int) -> dict[str, object]:
        response = self.client.post(
            "/api/quiz-sessions",
            json={"module_id": module_id, "count": count},
            headers=self.user_headers(user_id),
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def submit_quiz_item(
        self,
        user_id: int,
        session_id: int,
        item_id: int,
        answers: list[str],
    ) -> dict[str, object]:
        response = self.client.post(
            f"/api/quiz-sessions/{session_id}/items/{item_id}/submit",
            json={"answers": answers},
            headers=self.user_headers(user_id),
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def get_stats_payload(self, user_id: int, module_id: int | None = None) -> dict[str, object]:
        params = {"module_id": module_id} if module_id is not None else None
        response = self.client.get(
            "/api/stats",
            params=params,
            headers=self.user_headers(user_id),
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def set_review_flag(self, user_id: int, question_id: int, review_flag: bool = True) -> dict[str, object]:
        response = self.client.patch(
            f"/api/questions/{question_id}/review-flag",
            json={"review_flag": review_flag},
            headers=self.user_headers(user_id),
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def validate_import_payload(
        self,
        module_id: int,
        *,
        qml_text: str | None = None,
        rows: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {"module_id": module_id}
        if qml_text is not None:
            payload["qml_text"] = qml_text
        if rows is not None:
            payload["rows"] = rows
        response = self.client.post("/api/question-imports/validate", json=payload, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def commit_import_payload(self, module_id: int, rows: list[dict[str, object]]) -> dict[str, object]:
        response = self.client.post(
            "/api/question-imports/commit",
            json={"module_id": module_id, "rows": rows},
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        return response.json()
