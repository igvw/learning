import base64
import hashlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.database import get_connection, initialize_database
from backend.app.main import create_app
from backend.app.settings import auth_cookie_name
from test_support import (
    APP_DATABASE_URL,
    CONTENT_DIR,
    TEST_DATABASE_URL,
    PostgresBackendTestCase,
    ensure_test_database_exists,
    reset_test_database,
    validate_test_database_url,
)


class AuthApiTests(PostgresBackendTestCase):
    def test_new_user_passwords_use_the_library_backed_hash_format(self) -> None:
        user = self.create_user(handle="alice", display_name="Alice")

        with get_connection(TEST_DATABASE_URL) as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertTrue(row["password_hash"].startswith("$argon2"))
        self.assertFalse(row["password_hash"].startswith("scrypt:"))

    def test_password_reset_uses_the_library_backed_hash_format(self) -> None:
        user = self.create_user(handle="alice", display_name="Alice")

        response = self.client.post(
            f"/api/users/{user['id']}/password",
            json={"password": "updated-password123"},
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)

        with get_connection(TEST_DATABASE_URL) as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertTrue(row["password_hash"].startswith("$argon2"))
        self.assertFalse(row["password_hash"].startswith("scrypt:"))

    def test_legacy_scrypt_hashes_still_log_in_and_upgrade_in_place(self) -> None:
        user = self.create_user(handle="alice", display_name="Alice")
        legacy_hash = _legacy_scrypt_hash("password123")

        with get_connection(TEST_DATABASE_URL) as connection:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (legacy_hash, user["id"]),
            )

        login_response = self.client.post(
            "/api/auth/login",
            json={"handle": "alice", "password": "password123"},
        )
        self.assertEqual(login_response.status_code, 200)

        with get_connection(TEST_DATABASE_URL) as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertTrue(row["password_hash"].startswith("$argon2"))
        self.assertFalse(row["password_hash"].startswith("scrypt:"))

    def test_malformed_password_hashes_fail_closed(self) -> None:
        user = self.create_user(handle="alice", display_name="Alice")

        with get_connection(TEST_DATABASE_URL) as connection:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                ("$not-a-real-password-hash", user["id"]),
            )

        login_response = self.client.post(
            "/api/auth/login",
            json={"handle": "alice", "password": "password123"},
        )
        self.assertEqual(login_response.status_code, 400)
        self.assertEqual(login_response.json()["detail"], "Invalid handle or password.")

    def test_login_me_logout_and_demo_session(self) -> None:
        self.create_user(handle="alice", display_name="Alice")
        self.client.cookies.clear()

        login_response = self.client.post(
            "/api/auth/login",
            json={"handle": "alice", "password": "password123"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["handle"], "alice")
        self.assertEqual(login_response.cookies.get(auth_cookie_name()), self.client.cookies.get(auth_cookie_name()))

        me_response = self.client.get("/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(
            me_response.json(),
            {
                "id": 2,
                "handle": "alice",
                "display_name": "Alice",
                "role": "user",
                "is_demo": False,
                "created_at": login_response.json()["created_at"],
            },
        )

        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)
        self.assertIsNone(logout_response.json())
        self.assertIsNone(self.client.cookies.get(auth_cookie_name()))

        me_after_logout = self.client.get("/api/auth/me")
        self.assertEqual(me_after_logout.status_code, 401)
        self.assertEqual(me_after_logout.json()["detail"], "Authentication is required.")

        demo_response = self.client.post("/api/auth/demo-session")
        self.assertEqual(demo_response.status_code, 200)
        self.assertEqual(
            demo_response.json(),
            {
                "id": None,
                "handle": "demo",
                "display_name": "Demo",
                "role": "demo",
                "is_demo": True,
                "created_at": demo_response.json()["created_at"],
            },
        )

        demo_me_response = self.client.get("/api/auth/me")
        self.assertEqual(demo_me_response.status_code, 200)
        self.assertEqual(demo_me_response.json()["role"], "demo")
        self.assertTrue(demo_me_response.json()["is_demo"])

    def test_demo_mode_cannot_save_changes(self) -> None:
        self.client.post("/api/auth/demo-session")

        create_question_response = self.client.post(
            "/api/questions",
            json={
                "module_id": 1,
                "prompt": "demo prompt",
                "question_type": "single_text",
                "rank": 1,
                "accepted_answers": [["demo"]],
                "segments": [],
            },
        )
        self.assertEqual(create_question_response.status_code, 403)
        self.assertEqual(create_question_response.json()["detail"], "Demo mode does not save changes.")

    def test_admin_can_promote_and_demote_roles_when_another_admin_exists(self) -> None:
        ignazio = self.create_user(handle="ignazio", display_name="Ignazio")
        second_admin = self.create_user(handle="alice", display_name="Alice", role="admin")

        promote_response = self.client.patch(
            f"/api/users/{ignazio['id']}",
            json={"role": "admin"},
            headers=self.admin_headers,
        )
        self.assertEqual(promote_response.status_code, 200)
        self.assertEqual(
            promote_response.json(),
            {
                "id": ignazio["id"],
                "handle": "ignazio",
                "display_name": "Ignazio",
                "role": "admin",
                "created_at": ignazio["created_at"],
            },
        )

        demote_response = self.client.patch(
            f"/api/users/{second_admin['id']}",
            json={"role": "user"},
            headers=self.admin_headers,
        )
        self.assertEqual(demote_response.status_code, 200)
        self.assertEqual(demote_response.json()["role"], "user")

    def test_last_admin_cannot_be_demoted(self) -> None:
        demote_response = self.client.patch(
            f"/api/users/{self.admin_user['id']}",
            json={"role": "user"},
            headers=self.admin_headers,
        )
        self.assertEqual(demote_response.status_code, 400)
        self.assertEqual(demote_response.json()["detail"], "At least one admin account must remain.")

    def test_non_admin_cannot_update_roles(self) -> None:
        ignazio = self.create_user(handle="ignazio", display_name="Ignazio")
        regular_user = self.create_user(handle="alice", display_name="Alice")

        response = self.client.patch(
            f"/api/users/{ignazio['id']}",
            json={"role": "admin"},
            headers=self.user_headers(int(regular_user["id"])),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Admin access is required.")


class AuthEnvBootstrapApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        validate_test_database_url(TEST_DATABASE_URL, APP_DATABASE_URL)
        ensure_test_database_exists(TEST_DATABASE_URL)
        initialize_database(TEST_DATABASE_URL)

    def setUp(self) -> None:
        reset_test_database(TEST_DATABASE_URL)

    def test_env_bootstrap_creates_the_first_admin_on_startup(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ["LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE"] = "admin"
            os.environ["LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME"] = "Admin"
            os.environ["LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD"] = "password123"

            with TestClient(create_app(database_url=TEST_DATABASE_URL, content_root=CONTENT_DIR)) as client:
                health_response = client.get("/api/health")
                self.assertEqual(health_response.status_code, 200)
                self.assertFalse(health_response.json()["bootstrap_required"])

                login_response = client.post(
                    "/api/auth/login",
                    json={"handle": "admin", "password": "password123"},
                )
                self.assertEqual(login_response.status_code, 200)
                self.assertEqual(login_response.json()["role"], "admin")

        with get_connection(TEST_DATABASE_URL) as connection:
            rows = connection.execute(
                "SELECT handle, display_name, role FROM users ORDER BY id ASC"
            ).fetchall()
        self.assertEqual(
            rows,
            [{"handle": "admin", "display_name": "Admin", "role": "admin"}],
        )

    def test_manual_bootstrap_still_works_when_env_bootstrap_is_incomplete(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ["LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE"] = "admin"
            os.environ.pop("LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME", None)
            os.environ.pop("LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD", None)

            with TestClient(create_app(database_url=TEST_DATABASE_URL, content_root=CONTENT_DIR)) as client:
                health_response = client.get("/api/health")
                self.assertEqual(health_response.status_code, 200)
                self.assertTrue(health_response.json()["bootstrap_required"])

                bootstrap_response = client.post(
                    "/api/auth/bootstrap-admin",
                    json={"handle": "admin", "display_name": "Admin", "password": "password123"},
                )
                self.assertEqual(bootstrap_response.status_code, 200)
                self.assertEqual(bootstrap_response.json()["role"], "admin")

    def test_existing_admin_is_not_duplicated_by_env_bootstrap_on_restart(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ["LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE"] = "admin"
            os.environ["LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME"] = "Admin"
            os.environ["LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD"] = "password123"

            with TestClient(create_app(database_url=TEST_DATABASE_URL, content_root=CONTENT_DIR)) as first_client:
                first_health = first_client.get("/api/health")
                self.assertEqual(first_health.status_code, 200)
                self.assertFalse(first_health.json()["bootstrap_required"])

            with TestClient(create_app(database_url=TEST_DATABASE_URL, content_root=CONTENT_DIR)) as second_client:
                second_health = second_client.get("/api/health")
                self.assertEqual(second_health.status_code, 200)
                self.assertFalse(second_health.json()["bootstrap_required"])

        with get_connection(TEST_DATABASE_URL) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin'"
            ).fetchone()
        self.assertEqual(int(row["admin_count"]), 1)


def _legacy_scrypt_hash(password: str) -> str:
    salt = b"0123456789abcdef"
    digest = hashlib.scrypt(
        password.strip().encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    return ":".join(
        [
            "scrypt",
            str(2**14),
            "8",
            "1",
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )
