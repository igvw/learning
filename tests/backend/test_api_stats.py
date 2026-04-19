from backend.app.database import get_connection
from test_support import PostgresBackendTestCase


class StatsApiTests(PostgresBackendTestCase):
    def test_stats_include_first_asked_at_for_answered_questions_only(self) -> None:
        geography = self.create_module_record("First Seen Geography")
        capitals = self.create_module_record("First Seen Capitals", geography["id"])
        answered_question_id = self.create_question_record(
            capitals["id"],
            "What is the capital of Norway?",
            [["Oslo"]],
            rank=1,
        )["question_id"]
        unseen_question_id = self.create_question_record(
            capitals["id"],
            "What is the capital of Sweden?",
            [["Stockholm"]],
            rank=2,
        )["question_id"]

        user = self.create_user("alice-stats", "Alice Stats")

        with get_connection(self.database_url) as connection:
            first_session_id = connection.execute(
                """
                INSERT INTO quiz_sessions (user_id, module_id, created_at, completed_at)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """,
                (user["id"], capitals["id"], "2026-04-01T09:00:00Z", "2026-04-01T09:15:00Z"),
            ).fetchone()["id"]
            connection.execute(
                """
                INSERT INTO quiz_session_items (session_id, question_id, score_earned, score_possible)
                VALUES (?, ?, ?, ?)
                """,
                (first_session_id, answered_question_id, 1.0, 1.0),
            )

            second_session_id = connection.execute(
                """
                INSERT INTO quiz_sessions (user_id, module_id, created_at, completed_at)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """,
                (user["id"], capitals["id"], "2026-04-03T10:00:00Z", "2026-04-03T10:20:00Z"),
            ).fetchone()["id"]
            connection.execute(
                """
                INSERT INTO quiz_session_items (session_id, question_id, score_earned, score_possible)
                VALUES (?, ?, ?, ?)
                """,
                (second_session_id, answered_question_id, 0.0, 1.0),
            )

        stats_payload = self.get_stats_payload(user["id"], capitals["id"])
        questions_by_id = {row["question_id"]: row for row in stats_payload["questions"]}

        self.assertEqual(stats_payload["schedule_timezone"], "UTC")
        self.assertEqual(questions_by_id[answered_question_id]["first_asked_at"], "2026-04-01T09:15:00Z")
        self.assertEqual(questions_by_id[answered_question_id]["last_asked_at"], "2026-04-03T10:20:00Z")
        self.assertEqual(questions_by_id[unseen_question_id]["first_asked_at"], None)
        self.assertEqual(questions_by_id[unseen_question_id]["last_asked_at"], None)
