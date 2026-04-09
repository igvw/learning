from __future__ import annotations

import os

from test_support import PostgresBackendTestCase


class PostgresBackendIntegrationTests(PostgresBackendTestCase):
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

    def test_review_flagged_questions_do_not_reappear_in_quiz(self) -> None:
        user = self.client.post(
            "/api/users",
            json={"handle": "alice", "display_name": "Alice"},
        ).json()

        stats_response = self.client.get(
            "/api/stats",
            params={"module_id": 5},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(stats_response.status_code, 200)
        flagged_question_id = stats_response.json()["questions"][0]["question_id"]

        flag_response = self.client.patch(
            f"/api/questions/{flagged_question_id}/review-flag",
            json={"review_flag": True},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(flag_response.status_code, 200)

        session_response = self.client.post(
            "/api/quiz-sessions",
            json={"module_id": 5, "count": 10},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(session_response.status_code, 200)
        returned_ids = [item["question_id"] for item in session_response.json()["items"]]
        self.assertNotIn(flagged_question_id, returned_ids)
