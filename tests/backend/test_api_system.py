import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from test_support import PostgresBackendTestCase
from backend.app.settings import (
    auth_cookie_secure,
    auth_session_ttl_seconds,
    bootstrap_admin_credentials,
    cors_origins,
    demo_session_ttl_seconds,
    resolve_database_url,
    schedule_timezone_name,
    seed_on_boot,
)


class SystemApiTests(PostgresBackendTestCase):
    def test_users_can_be_created_and_listed(self) -> None:
        create_response = self.client.post(
            "/api/users",
            json={"handle": "alice", "display_name": "Alice", "role": "user", "password": "password123"},
            headers=self.admin_headers,
        )
        self.assertEqual(create_response.status_code, 200)

        list_response = self.client.get("/api/users", headers=self.admin_headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            list_response.json(),
            [
                {
                    "id": 1,
                    "handle": "admin",
                    "display_name": "Admin",
                    "role": "admin",
                    "created_at": self.admin_user["created_at"],
                },
                {
                    "id": 2,
                    "handle": "alice",
                    "display_name": "Alice",
                    "role": "user",
                    "created_at": create_response.json()["created_at"],
                }
            ],
        )

    def test_health_includes_instance_key(self) -> None:
        original_instance_key = os.environ.get("LEARNING_APP_INSTANCE_KEY")
        os.environ["LEARNING_APP_INSTANCE_KEY"] = "test-suite"
        try:
            response = self.client.get("/api/health")
        finally:
            if original_instance_key is None:
                os.environ.pop("LEARNING_APP_INSTANCE_KEY", None)
            else:
                os.environ["LEARNING_APP_INSTANCE_KEY"] = original_instance_key

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "instance_key": "test-suite",
                "bootstrap_required": False,
            },
        )

    def test_resolve_database_url_requires_runtime_settings(self) -> None:
        previous_values = {
            "LEARNING_APP_DATABASE_URL": os.environ.get("LEARNING_APP_DATABASE_URL"),
            "POSTGRES_DB": os.environ.get("POSTGRES_DB"),
            "POSTGRES_USER": os.environ.get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        }
        try:
            for name in previous_values:
                os.environ.pop(name, None)
            with self.assertRaisesRegex(RuntimeError, "Database configuration is missing"):
                resolve_database_url()
        finally:
            for name, value in previous_values.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


class SettingsUnitTests(unittest.TestCase):
    def test_resolve_database_url_uses_explicit_app_database_url(self) -> None:
        with patch.dict(
            os.environ,
            {"LEARNING_APP_DATABASE_URL": "  postgresql://example/app  "},
            clear=True,
        ):
            self.assertEqual(resolve_database_url(), "postgresql://example/app")

    def test_resolve_database_url_builds_from_postgres_settings(self) -> None:
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DB": "learning",
                "POSTGRES_USER": "user@example.com",
                "POSTGRES_PASSWORD": "p@ss word",
                "POSTGRES_HOST": "db.local",
                "POSTGRES_PORT": "6543",
            },
            clear=True,
        ):
            self.assertEqual(
                resolve_database_url(),
                "postgresql://user%40example.com:p%40ss%20word@db.local:6543/learning",
            )

    def test_resolve_database_url_rejects_incomplete_postgres_settings(self) -> None:
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DB": "learning",
                "POSTGRES_USER": "learning",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "Database configuration is incomplete"):
                resolve_database_url()

    def test_bootstrap_admin_credentials_require_all_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE": "admin",
                "LEARNING_APP_BOOTSTRAP_ADMIN_DISPLAY_NAME": "Admin",
                "LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD": "password123",
            },
            clear=True,
        ):
            self.assertEqual(bootstrap_admin_credentials(), ("admin", "Admin", "password123"))

        with patch.dict(
            os.environ,
            {
                "LEARNING_APP_BOOTSTRAP_ADMIN_HANDLE": "admin",
                "LEARNING_APP_BOOTSTRAP_ADMIN_PASSWORD": "password123",
            },
            clear=True,
        ):
            self.assertIsNone(bootstrap_admin_credentials())

    def test_boolean_and_ttl_settings_are_typed_and_bounded(self) -> None:
        with patch.dict(
            os.environ,
            {
                "LEARNING_APP_SEED_ON_BOOT": "false",
                "LEARNING_APP_AUTH_COOKIE_SECURE": "yes",
                "LEARNING_APP_AUTH_SESSION_TTL_SECONDS": "30",
                "LEARNING_APP_DEMO_SESSION_TTL_SECONDS": "120",
            },
            clear=True,
        ):
            self.assertFalse(seed_on_boot())
            self.assertTrue(auth_cookie_secure())
            self.assertEqual(auth_session_ttl_seconds(), 60)
            self.assertEqual(demo_session_ttl_seconds(), 120)

    def test_cors_origins_use_dev_defaults_when_not_explicitly_configured(self) -> None:
        with patch.dict(
            os.environ,
            {"LEARNING_APP_ENV": "development"},
            clear=True,
        ):
            self.assertEqual(
                cors_origins(),
                ["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5173"],
            )

    def test_cors_origins_use_explicit_list_when_configured(self) -> None:
        with patch.dict(
            os.environ,
            {
                "LEARNING_APP_CORS_ORIGINS": "https://a.example, https://b.example ",
                "LEARNING_APP_ENV": "production",
            },
            clear=True,
        ):
            self.assertEqual(cors_origins(), ["https://a.example", "https://b.example"])

    def test_schedule_timezone_defaults_to_utc(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(schedule_timezone_name(), "UTC")

    def test_schedule_timezone_rejects_unknown_zone(self) -> None:
        with patch.dict(
            os.environ,
            {"LEARNING_APP_SCHEDULE_TIMEZONE": "Mars/Olympus"},
            clear=True,
        ):
            with self.assertRaises(ValidationError):
                schedule_timezone_name()
