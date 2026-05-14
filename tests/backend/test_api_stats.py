from backend.app.database import get_connection
from backend.app.service.stats import _build_study_blocks
from test_support import PostgresBackendTestCase


class StatsApiTests(PostgresBackendTestCase):
    def test_study_blocks_split_on_thirty_minute_activity_gaps(self) -> None:
        blocks = _build_study_blocks(
            [
                {"id": 1, "answered_at": "2026-04-01T09:00:00+00:00", "score_earned": 1.0, "score_possible": 1.0},
                {"id": 2, "answered_at": "2026-04-01T09:29:00+00:00", "score_earned": 0.0, "score_possible": 1.0},
                {"id": 3, "answered_at": "2026-04-01T09:59:00+00:00", "score_earned": 1.0, "score_possible": 1.0},
                {"id": 4, "answered_at": "2026-04-01T10:28:00+00:00", "score_earned": 1.0, "score_possible": 1.0},
                {"id": 5, "answered_at": "2026-04-01T11:00:00+00:00", "score_earned": 1.0, "score_possible": 1.0},
            ],
            now="2026-04-03T08:00:00+00:00",
        )

        self.assertEqual([block["answered_count"] for block in blocks], [2, 2, 1])
        self.assertEqual(blocks[0]["started_at"], "2026-04-01T09:00:00+00:00")
        self.assertEqual(blocks[0]["ended_at"], "2026-04-01T09:29:00+00:00")
        self.assertEqual(blocks[1]["started_at"], "2026-04-01T09:59:00+00:00")
        self.assertEqual([block["day_label"] for block in blocks], ["2d", "2d", "2d"])
        self.assertEqual(blocks[0]["correct_count"], 1.0)
        self.assertEqual(blocks[0]["score_possible"], 2.0)
        self.assertEqual(blocks[0]["accuracy"], 0.5)
        self.assertEqual(blocks[0]["duration_minutes"], 29.0)
        self.assertAlmostEqual(blocks[0]["answers_per_minute"], 2 / 29)
        self.assertEqual(blocks[2]["duration_minutes"], 1.0)
        self.assertEqual(blocks[2]["answers_per_minute"], 1.0)

    def test_study_blocks_keep_the_latest_twenty_blocks_by_default(self) -> None:
        rows = [
            {
                "id": index,
                "answered_at": f"2026-04-{index:02d}T09:00:00+00:00",
                "score_earned": 1.0,
                "score_possible": 1.0,
            }
            for index in range(1, 23)
        ]

        blocks = _build_study_blocks(rows, now="2026-04-23T08:00:00+00:00")

        self.assertEqual(len(blocks), 20)
        self.assertEqual(blocks[0]["started_at"], "2026-04-03T09:00:00+00:00")
        self.assertEqual(blocks[-1]["started_at"], "2026-04-22T09:00:00+00:00")

    def test_stats_include_study_blocks_for_selected_module_scope(self) -> None:
        geography = self.create_module_record("Study Block Geography")
        capitals = self.create_module_record("Study Block Capitals", geography["id"])
        biology = self.create_module_record("Study Block Biology")
        user = self.create_user("alice-study-blocks", "Alice Study Blocks")
        other_user = self.create_user("bob-study-blocks", "Bob Study Blocks")
        question_ids = [
            self.create_question_record(
                capitals["id"],
                f"What is capital test {index}?",
                [[f"answer-{index}"]],
                rank=index,
            )["question_id"]
            for index in range(1, 4)
        ]
        other_module_question_id = self.create_question_record(
            biology["id"],
            "What is outside the selected scope?",
            [["outside"]],
            rank=1,
        )["question_id"]

        def insert_attempt(
            user_id: int,
            module_id: int,
            question_id: int,
            answered_at: str,
            score_earned: float = 1.0,
            score_possible: float = 1.0,
        ) -> None:
            with get_connection(self.database_url) as connection:
                session_id = connection.execute(
                    """
                    INSERT INTO quiz_sessions (user_id, module_id, created_at, completed_at)
                    VALUES (?, ?, ?, ?)
                    RETURNING id
                    """,
                    (user_id, module_id, answered_at, answered_at),
                ).fetchone()["id"]
                connection.execute(
                    """
                    INSERT INTO quiz_session_items (session_id, question_id, score_earned, score_possible)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, question_id, score_earned, score_possible),
                )
                connection.execute(
                    """
                    INSERT INTO attempts (
                        session_id,
                        user_id,
                        question_id,
                        module_id,
                        score_earned,
                        score_possible,
                        answered_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, user_id, question_id, module_id, score_earned, score_possible, answered_at),
                )

        insert_attempt(int(user["id"]), capitals["id"], int(question_ids[0]), "2026-04-01T09:00:00+00:00")
        insert_attempt(
            int(user["id"]),
            capitals["id"],
            int(question_ids[1]),
            "2026-04-01T09:10:00+00:00",
            score_earned=0.0,
        )
        insert_attempt(int(user["id"]), capitals["id"], int(question_ids[2]), "2026-04-01T09:40:00+00:00")
        insert_attempt(int(user["id"]), biology["id"], int(other_module_question_id), "2026-04-01T09:15:00+00:00")
        insert_attempt(int(other_user["id"]), capitals["id"], int(question_ids[0]), "2026-04-01T09:20:00+00:00")

        stats_payload = self.get_stats_payload(int(user["id"]), capitals["id"])

        self.assertEqual([block["answered_count"] for block in stats_payload["study_blocks"]], [2, 1])
        self.assertEqual(stats_payload["study_blocks"][0]["started_at"], "2026-04-01T09:00:00+00:00")
        self.assertEqual(stats_payload["study_blocks"][0]["ended_at"], "2026-04-01T09:10:00+00:00")
        self.assertEqual(stats_payload["study_blocks"][0]["correct_count"], 1.0)
        self.assertEqual(stats_payload["study_blocks"][0]["score_possible"], 2.0)
        self.assertEqual(stats_payload["study_blocks"][0]["accuracy"], 0.5)
        self.assertEqual(stats_payload["study_blocks"][0]["duration_minutes"], 10.0)
        self.assertEqual(stats_payload["study_blocks"][0]["answers_per_minute"], 0.2)
        self.assertEqual(stats_payload["study_blocks"][1]["started_at"], "2026-04-01T09:40:00+00:00")

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
            connection.execute(
                """
                INSERT INTO attempts (
                    session_id,
                    user_id,
                    question_id,
                    module_id,
                    score_earned,
                    score_possible,
                    answered_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    first_session_id,
                    user["id"],
                    answered_question_id,
                    capitals["id"],
                    1.0,
                    1.0,
                    "2026-04-01T09:15:00Z",
                ),
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
            connection.execute(
                """
                INSERT INTO attempts (
                    session_id,
                    user_id,
                    question_id,
                    module_id,
                    score_earned,
                    score_possible,
                    answered_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    second_session_id,
                    user["id"],
                    answered_question_id,
                    capitals["id"],
                    0.0,
                    1.0,
                    "2026-04-03T10:20:00Z",
                ),
            )

        stats_payload = self.get_stats_payload(user["id"], capitals["id"])
        questions_by_id = {row["question_id"]: row for row in stats_payload["questions"]}

        self.assertEqual(stats_payload["schedule_timezone"], "UTC")
        self.assertEqual(questions_by_id[answered_question_id]["first_asked_at"], "2026-04-01T09:15:00Z")
        self.assertEqual(questions_by_id[answered_question_id]["last_asked_at"], "2026-04-03T10:20:00Z")
        self.assertEqual(questions_by_id[unseen_question_id]["first_asked_at"], None)
        self.assertEqual(questions_by_id[unseen_question_id]["last_asked_at"], None)
