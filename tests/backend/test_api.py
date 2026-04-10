from __future__ import annotations

import os

from backend.app.database import get_connection
from backend.app.schemas import QuestionDraftIn
from backend.app.services import create_module, create_question
from test_support import PostgresBackendTestCase


class PostgresBackendIntegrationTests(PostgresBackendTestCase):
    def _create_module_tree(self) -> dict[str, int]:
        with get_connection(self.database_url) as connection:
            norwegian = create_module(connection, title="Norwegian", parent_id=None, instruction="")
            vocabulary = create_module(connection, title="Vocabulary", parent_id=norwegian["id"], instruction="")
            source_a = create_module(connection, title="Source A", parent_id=vocabulary["id"], instruction="")
            source_b = create_module(connection, title="Source B", parent_id=vocabulary["id"], instruction="")
            target = create_module(connection, title="Target", parent_id=vocabulary["id"], instruction="")
        return {
            "norwegian": norwegian["id"],
            "vocabulary": vocabulary["id"],
            "source_a": source_a["id"],
            "source_b": source_b["id"],
            "target": target["id"],
        }

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

    def test_leaf_module_can_be_renamed_without_losing_question_access(self) -> None:
        with get_connection(self.database_url) as connection:
            norwegian = create_module(connection, title="Norwegian", parent_id=None, instruction="")
            nouns = create_module(
                connection,
                title="Nouns to English",
                parent_id=norwegian["id"],
                instruction="Translate the Norwegian term into English.",
            )
            create_question(
                connection,
                QuestionDraftIn(
                    module_id=nouns["id"],
                    prompt="hund",
                    question_type="single_text",
                    rank=1,
                    accepted_answers=[["dog"]],
                    segments=[],
                ),
            )

        rename_response = self.client.patch(
            f"/api/modules/{nouns['id']}",
            json={
                "title": "Animals to English",
                "instruction": "Translate the animal term into English.",
            },
        )
        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(rename_response.json()["full_slug"], "norwegian/animals_to_english")
        self.assertEqual(rename_response.json()["instruction"], "Translate the animal term into English.")

        tree_response = self.client.get("/api/modules/tree")
        self.assertEqual(tree_response.status_code, 200)
        renamed_parent = next(node for node in tree_response.json() if node["id"] == norwegian["id"])
        self.assertEqual(renamed_parent["full_slug"], "norwegian")
        self.assertEqual(
            renamed_parent["children"],
            [
                {
                    "id": nouns["id"],
                    "title": "Animals To English",
                    "slug": "animals_to_english",
                    "full_slug": "norwegian/animals_to_english",
                    "instruction": "Translate the animal term into English.",
                    "children": [],
                }
            ],
        )

        user = self.client.post(
            "/api/users",
            json={"handle": "alice", "display_name": "Alice"},
        ).json()
        stats_response = self.client.get(
            "/api/stats",
            params={"module_id": nouns["id"]},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(stats_response.status_code, 200)
        self.assertEqual(stats_response.json()["questions"][0]["module_full_slug"], "norwegian/animals_to_english")
        self.assertEqual(stats_response.json()["questions"][0]["prompt"], "hund")

    def test_non_leaf_module_rename_is_rejected(self) -> None:
        with get_connection(self.database_url) as connection:
            norwegian = create_module(connection, title="Norwegian", parent_id=None, instruction="")
            create_module(connection, title="Vocabulary", parent_id=norwegian["id"], instruction="")

        rename_response = self.client.patch(
            f"/api/modules/{norwegian['id']}",
            json={"title": "Language", "instruction": ""},
        )
        self.assertEqual(rename_response.status_code, 400)
        self.assertEqual(rename_response.json()["detail"], "Only leaf modules can be renamed.")

    def test_same_tree_reimport_moves_question_and_preserves_progress(self) -> None:
        module_ids = self._create_module_tree()
        with get_connection(self.database_url) as connection:
            question_id = create_question(
                connection,
                QuestionDraftIn(
                    module_id=module_ids["source_a"],
                    prompt="hund",
                    question_type="single_text",
                    rank=1,
                    accepted_answers=[["dog"]],
                    segments=[],
                ),
            )["question_id"]

        user = self.client.post(
            "/api/users",
            json={"handle": "alice", "display_name": "Alice"},
        ).json()
        session_response = self.client.post(
            "/api/quiz-sessions",
            json={"module_id": module_ids["source_a"], "count": 1},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(session_response.status_code, 200)
        item = session_response.json()["items"][0]
        self.client.post(
            f"/api/quiz-sessions/{session_response.json()['id']}/items/{item['id']}/submit",
            json={"answers": ["dog"]},
            headers={"X-User-Id": str(user["id"])},
        )
        self.client.patch(
            f"/api/questions/{question_id}/review-flag",
            json={"review_flag": True},
            headers={"X-User-Id": str(user["id"])},
        )

        validate_response = self.client.post(
            "/api/question-imports/validate",
            json={"module_id": module_ids["target"], "qml_text": "hund [dog]"},
        )
        self.assertEqual(validate_response.status_code, 200)
        validate_payload = validate_response.json()
        self.assertEqual(validate_payload["relocation_rows"][0]["status"], "move")
        self.assertTrue(validate_payload["relocation_rows"][0]["ready_without_edit"])

        commit_response = self.client.post(
            "/api/question-imports/commit",
            json={
                "module_id": module_ids["target"],
                "rows": [{"row_number": 1, "qml_line": "hund [dog]"}],
            },
        )
        self.assertEqual(commit_response.status_code, 200)
        self.assertTrue(commit_response.json()["committed"])

        source_stats = self.client.get(
            "/api/stats",
            params={"module_id": module_ids["source_a"]},
            headers={"X-User-Id": str(user["id"])},
        ).json()
        self.assertEqual(source_stats["questions"], [])

        target_stats = self.client.get(
            "/api/stats",
            params={"module_id": module_ids["target"]},
            headers={"X-User-Id": str(user["id"])},
        ).json()
        self.assertEqual(len(target_stats["questions"]), 1)
        self.assertEqual(target_stats["questions"][0]["question_id"], question_id)
        self.assertEqual(target_stats["questions"][0]["attempts"], 1)
        self.assertFalse(target_stats["questions"][0]["review_flag"])

    def test_same_tree_merge_keeps_one_question_and_resets_review_flags(self) -> None:
        module_ids = self._create_module_tree()
        with get_connection(self.database_url) as connection:
            first_question_id = create_question(
                connection,
                QuestionDraftIn(
                    module_id=module_ids["source_a"],
                    prompt="hund",
                    question_type="single_text",
                    rank=1,
                    accepted_answers=[["dog"]],
                    segments=[],
                ),
            )["question_id"]
            second_question_id = create_question(
                connection,
                QuestionDraftIn(
                    module_id=module_ids["source_b"],
                    prompt="hund",
                    question_type="single_text",
                    rank=1,
                    accepted_answers=[["canine"]],
                    segments=[],
                ),
            )["question_id"]

        user = self.client.post(
            "/api/users",
            json={"handle": "bob", "display_name": "Bob"},
        ).json()
        session_response = self.client.post(
            "/api/quiz-sessions",
            json={"module_id": module_ids["source_b"], "count": 1},
            headers={"X-User-Id": str(user["id"])},
        )
        self.assertEqual(session_response.status_code, 200)
        item = session_response.json()["items"][0]
        self.client.post(
            f"/api/quiz-sessions/{session_response.json()['id']}/items/{item['id']}/submit",
            json={"answers": ["wrong"]},
            headers={"X-User-Id": str(user["id"])},
        )
        self.client.patch(
            f"/api/questions/{first_question_id}/review-flag",
            json={"review_flag": True},
            headers={"X-User-Id": str(user["id"])},
        )
        self.client.patch(
            f"/api/questions/{second_question_id}/review-flag",
            json={"review_flag": True},
            headers={"X-User-Id": str(user["id"])},
        )

        validate_response = self.client.post(
            "/api/question-imports/validate",
            json={"module_id": module_ids["target"], "qml_text": "hund [dog | canine | pooch]"},
        )
        self.assertEqual(validate_response.status_code, 200)
        validate_payload = validate_response.json()
        self.assertEqual(validate_payload["relocation_rows"][0]["status"], "merge")
        self.assertEqual(len(validate_payload["relocation_rows"][0]["matched_questions"]), 2)

        commit_response = self.client.post(
            "/api/question-imports/commit",
            json={
                "module_id": module_ids["target"],
                "rows": [{"row_number": 1, "qml_line": "hund [dog | canine | pooch]"}],
            },
        )
        self.assertEqual(commit_response.status_code, 200)
        self.assertTrue(commit_response.json()["committed"])

        target_stats = self.client.get(
            "/api/stats",
            params={"module_id": module_ids["target"]},
            headers={"X-User-Id": str(user["id"])},
        ).json()
        self.assertEqual(len(target_stats["questions"]), 1)
        self.assertEqual(target_stats["questions"][0]["question_id"], min(first_question_id, second_question_id))
        self.assertEqual(target_stats["questions"][0]["attempts"], 1)
        self.assertFalse(target_stats["questions"][0]["review_flag"])
        self.assertEqual(target_stats["questions"][0]["accepted_answers"], [["dog", "canine", "pooch"]])

        with get_connection(self.database_url) as connection:
            question_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM questions WHERE prompt = ? ORDER BY id ASC",
                    ("hund",),
                ).fetchall()
            ]
        self.assertEqual(question_ids, [min(first_question_id, second_question_id)])
