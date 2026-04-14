import os

from test_support import PostgresBackendTestCase


class SystemApiTests(PostgresBackendTestCase):
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
            },
        )
