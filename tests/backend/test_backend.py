from __future__ import annotations

import random
import tempfile
import unittest
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.database import get_connection, initialize_database
from backend.app.main import create_app
from backend.app.schemas import QuestionDraftIn
from backend.app.services import (
    backfill_question_type_defaults,
    create_question,
    create_quiz_session,
    evaluate_answers,
    get_stats,
    revise_question,
    sync_seed_content,
    weighted_sample_without_replacement,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = REPO_ROOT / "content" / "modules"


def current_question_row(connection, *, question_id: int | None = None, source_id: str | None = None):
    if question_id is None and source_id is None:
        raise ValueError("question_id or source_id is required.")

    filters = []
    params: list[object] = []
    if question_id is not None:
        filters.append("q.id = ?")
        params.append(question_id)
    if source_id is not None:
        filters.append("q.source_id = ?")
        params.append(source_id)

    return connection.execute(
        f"""
        SELECT
            q.id AS question_id,
            q.module_id,
            q.question_type,
            q.prompt,
            q.ranking,
            q.type_config_json
        FROM questions AS q
        WHERE {" AND ".join(filters)}
        """,
        tuple(params),
    ).fetchone()


class LearningAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def build_client(self) -> TestClient:
        app = create_app(db_path=self.db_path, content_root=CONTENT_ROOT)
        return TestClient(app)

    def test_seed_import_is_idempotent(self) -> None:
        initialize_database(self.db_path)
        with get_connection(self.db_path) as connection:
            first = sync_seed_content(connection, CONTENT_ROOT)
            second = sync_seed_content(connection, CONTENT_ROOT)
            counts = connection.execute(
                "SELECT (SELECT COUNT(*) FROM modules), (SELECT COUNT(*) FROM questions)"
            ).fetchone()

        self.assertEqual(first, {"modules": 6, "questions": 20})
        self.assertEqual(second, {"modules": 0, "questions": 0})
        self.assertEqual(tuple(counts), (6, 20))

    def test_answer_evaluation_supports_all_question_types(self) -> None:
        single_correct = evaluate_answers("single_text", {"accepted_answers": [["chlorophyll"]]}, ["  Chlorophyll "])
        multi_unordered_correct = evaluate_answers(
            "multi_text",
            {"accepted_answers": [["white nile"], ["blue nile"]]},
            ["blue nile", "White Nile"],
        )
        multi_unordered_partial = evaluate_answers(
            "multi_text",
            {"accepted_answers": [["white nile"], ["blue nile"], ["atbara"]]},
            ["blue nile", "wrong", "white nile"],
        )
        ordered_multi_correct = evaluate_answers(
            "ordered_multi",
            {"accepted_answers": [["xylem"], ["phloem"]]},
            ["xylem", "PHLOEM"],
        )
        ordered_multi_wrong_order = evaluate_answers(
            "ordered_multi",
            {"accepted_answers": [["xylem"], ["phloem"]]},
            ["phloem", "xylem"],
        )
        inline_incorrect = evaluate_answers(
            "inline_cloze",
            {"accepted_answers": [["canberra"]]},
            ["Sydney"],
        )

        self.assertTrue(single_correct[0])
        self.assertEqual((single_correct[1], single_correct[2]), (1.0, 1.0))
        self.assertTrue(multi_unordered_correct[0])
        self.assertEqual((multi_unordered_correct[1], multi_unordered_correct[2]), (1.0, 1.0))
        self.assertFalse(multi_unordered_partial[0])
        self.assertAlmostEqual(multi_unordered_partial[1], 2 / 3)
        self.assertEqual(multi_unordered_partial[2], 1.0)
        self.assertTrue(multi_unordered_partial[3][0]["is_correct"])
        self.assertFalse(multi_unordered_partial[3][1]["is_correct"])
        self.assertTrue(multi_unordered_partial[3][2]["is_correct"])
        self.assertTrue(ordered_multi_correct[0])
        self.assertEqual((ordered_multi_correct[1], ordered_multi_correct[2]), (1.0, 1.0))
        self.assertFalse(ordered_multi_wrong_order[0])
        self.assertEqual((ordered_multi_wrong_order[1], ordered_multi_wrong_order[2]), (0.0, 1.0))
        self.assertFalse(inline_incorrect[0])
        self.assertEqual((inline_incorrect[1], inline_incorrect[2]), (0.0, 1.0))
        self.assertEqual(inline_incorrect[3][0]["expected"], "canberra")

    def test_multi_text_questions_do_not_require_slot_prompts(self) -> None:
        initialize_database(self.db_path)
        with get_connection(self.db_path) as connection:
            sync_seed_content(connection, CONTENT_ROOT)
            payload = QuestionDraftIn(
                module_id=2,
                prompt="Name two plant transport tissues.",
                question_type="multi_text",
                ranking=2,
                review_flag=False,
                accepted_answers=[["xylem"], ["phloem"]],
                slot_prompts=[],
                segments=[],
            )
            created = create_question(connection, payload)
            session = create_quiz_session(connection, module_id=2, count=50, rng=random.Random(0))
            created_item = next((item for item in session["items"] if item["question_id"] == created["question_id"]), None)

        self.assertIsNotNone(created_item)
        self.assertEqual(created_item["type_config"], {"expected_slots": 2})

    def test_weighted_sampling_prefers_unseen_questions(self) -> None:
        high_need = {
            "id": 1,
            "ranking": 1,
            "attempts_count": 0,
            "correct_count": 0,
            "incorrect_count": 0,
        }
        low_need = {
            "id": 2,
            "ranking": 1,
            "attempts_count": 25,
            "correct_count": 24,
            "incorrect_count": 1,
        }

        high_need_wins = 0
        for seed in range(200):
            selected = weighted_sample_without_replacement(
                [high_need, low_need],
                1,
                rng=random.Random(seed),
            )
            if selected[0]["id"] == 1:
                high_need_wins += 1

        self.assertGreater(high_need_wins, 150)

    def test_backfill_moves_legacy_ordered_multi_and_keeps_seeded_river_questions_unordered(self) -> None:
        initialize_database(self.db_path)
        with get_connection(self.db_path) as connection:
            sync_seed_content(connection, CONTENT_ROOT)

            manual_payload = QuestionDraftIn(
                module_id=2,
                prompt="Name the transport tissues in order.",
                question_type="multi_text",
                ranking=2,
                review_flag=False,
                accepted_answers=[["xylem"], ["phloem"]],
                slot_prompts=["First", "Second"],
                segments=[],
            )
            created = create_question(connection, manual_payload)

            connection.execute(
                """
                UPDATE questions
                SET type_config_json = ?
                WHERE id = ?
                """,
                (
                    json.dumps(
                        {
                            "accepted_answers": [["xylem"], ["phloem"]],
                            "answer_order_matters": True,
                            "segments": [],
                            "slot_prompts": ["First", "Second"],
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    created["question_id"],
                ),
            )

            khartoum = connection.execute(
                """
                SELECT id AS question_id
                FROM questions
                WHERE source_id = ?
                """,
                ("geography-rivers-002",),
            ).fetchone()
            connection.execute(
                """
                UPDATE questions
                SET question_type = ?, type_config_json = ?
                WHERE source_id = ?
                """,
                (
                    "ordered_multi",
                    json.dumps(
                        {
                            "accepted_answers": [["white nile"], ["blue nile"]],
                            "answer_order_matters": True,
                            "segments": [],
                            "slot_prompts": ["River 1", "River 2"],
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    "geography-rivers-002",
                ),
            )

            germany_rivers = connection.execute(
                """
                SELECT id AS question_id
                FROM questions
                WHERE source_id = ?
                """,
                ("geography-rivers-005",),
            ).fetchone()
            connection.execute(
                """
                UPDATE questions
                SET question_type = ?
                WHERE source_id = ?
                """,
                ("ordered_multi", "geography-rivers-005"),
            )

            backfill_question_type_defaults(connection)

            manual_question = current_question_row(connection, question_id=created["question_id"])
            khartoum_question = current_question_row(connection, source_id="geography-rivers-002")
            germany_rivers_question = current_question_row(connection, source_id="geography-rivers-005")
            khartoum_current = current_question_row(connection, source_id="geography-rivers-002")

        self.assertEqual(manual_question["question_type"], "ordered_multi")
        self.assertNotIn("answer_order_matters", manual_question["type_config_json"])
        self.assertEqual(khartoum_question["question_type"], "multi_text")
        self.assertNotIn("answer_order_matters", khartoum_question["type_config_json"])
        self.assertEqual(germany_rivers_question["question_type"], "multi_text")
        self.assertEqual(khartoum_current["question_type"], "multi_text")
        self.assertNotIn("answer_order_matters", khartoum_current["type_config_json"])

    def test_revision_reset_clears_current_question_stats(self) -> None:
        initialize_database(self.db_path)
        with get_connection(self.db_path) as connection:
            sync_seed_content(connection, CONTENT_ROOT)
            payload = QuestionDraftIn(
                module_id=2,
                prompt="Test prompt",
                question_type="single_text",
                ranking=3,
                review_flag=True,
                accepted_answers=[["test"]],
                slot_prompts=[],
                segments=[],
            )
            created = create_question(connection, payload)
            session_cursor = connection.execute(
                """
                INSERT INTO quiz_sessions (module_id, created_at, completed_at)
                VALUES (?, ?, ?)
                """,
                (payload.module_id, "2026-04-04T10:00:00+00:00", "2026-04-04T10:00:00+00:00"),
            )
            connection.execute(
                """
                INSERT INTO quiz_session_items (session_id, question_id, score_earned, score_possible)
                VALUES (?, ?, ?, ?)
                """,
                (session_cursor.lastrowid, created["question_id"], 0.5, 1.0),
            )

            stats_before = get_stats(connection, module_id=payload.module_id, review_only=False)
            revise_question(connection, created["question_id"], payload, reset_stats=False)
            stats_after_no_reset = get_stats(connection, module_id=payload.module_id, review_only=False)
            revise_question(connection, created["question_id"], payload, reset_stats=True)
            stats_after_reset = get_stats(connection, module_id=payload.module_id, review_only=False)

        before_row = next(question for question in stats_before["questions"] if question["question_id"] == created["question_id"])
        no_reset_row = next(question for question in stats_after_no_reset["questions"] if question["question_id"] == created["question_id"])
        reset_row = next(question for question in stats_after_reset["questions"] if question["question_id"] == created["question_id"])

        self.assertEqual(before_row["attempts"], 1)
        self.assertAlmostEqual(before_row["correct_percentage"], 0.5)
        self.assertEqual(no_reset_row["attempts"], 1)
        self.assertAlmostEqual(no_reset_row["correct_percentage"], 0.5)
        self.assertEqual(reset_row["attempts"], 0)
        self.assertEqual(reset_row["correct_percentage"], 0.0)
        self.assertTrue(reset_row["review_flag"])

    def test_stats_returns_latest_ten_sessions_in_chronological_order(self) -> None:
        initialize_database(self.db_path)
        with get_connection(self.db_path) as connection:
            sync_seed_content(connection, CONTENT_ROOT)
            seed_question = connection.execute(
                """
                SELECT
                    q.id AS question_id,
                    q.module_id,
                    q.prompt,
                    q.question_type,
                    q.ranking,
                    q.type_config_json
                FROM questions AS q
                ORDER BY q.id
                LIMIT 1
                """
            ).fetchone()
            other_question = connection.execute(
                """
                SELECT
                    q.id AS question_id,
                    q.module_id,
                    q.prompt,
                    q.question_type,
                    q.ranking,
                    q.type_config_json
                FROM questions AS q
                WHERE q.module_id != ?
                ORDER BY q.id
                LIMIT 1
                """,
                (seed_question["module_id"],),
            ).fetchone()

            for hour in range(1, 13):
                timestamp = f"2026-04-04T{hour:02d}:00:00+00:00"
                session_cursor = connection.execute(
                    """
                    INSERT INTO quiz_sessions (module_id, created_at, completed_at)
                    VALUES (?, ?, ?)
                    """,
                    (seed_question["module_id"], timestamp, timestamp),
                )
                connection.execute(
                    """
                    INSERT INTO quiz_session_items (session_id, question_id, score_earned, score_possible)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        session_cursor.lastrowid,
                        seed_question["question_id"],
                        1.0,
                        1.0,
                    ),
                )

            other_timestamp = "2026-04-04T13:00:00+00:00"
            other_session_cursor = connection.execute(
                """
                INSERT INTO quiz_sessions (module_id, created_at, completed_at)
                VALUES (?, ?, ?)
                """,
                (other_question["module_id"], other_timestamp, other_timestamp),
            )
            connection.execute(
                """
                INSERT INTO quiz_session_items (session_id, question_id, score_earned, score_possible)
                VALUES (?, ?, ?, ?)
                """,
                (
                    other_session_cursor.lastrowid,
                    other_question["question_id"],
                    1.0,
                    1.0,
                ),
            )

            stats = get_stats(connection, module_id=seed_question["module_id"], review_only=False)

        created_at_values = [session["created_at"] for session in stats["recent_sessions"]]
        self.assertEqual(len(created_at_values), 10)
        self.assertEqual(created_at_values, sorted(created_at_values))
        self.assertEqual(created_at_values[0], "2026-04-04T03:00:00+00:00")
        self.assertEqual(created_at_values[-1], "2026-04-04T12:00:00+00:00")
        self.assertNotIn(other_timestamp, created_at_values)

    def test_inline_cloze_preview_uses_underscore_blank_token(self) -> None:
        initialize_database(self.db_path)
        with get_connection(self.db_path) as connection:
            sync_seed_content(connection, CONTENT_ROOT)
            inline_row = connection.execute(
                """
                SELECT
                    q.module_id,
                    q.prompt,
                    q.question_type,
                    q.type_config_json
                FROM questions AS q
                WHERE q.question_type = 'inline_cloze'
                ORDER BY q.id
                LIMIT 1
                """
            ).fetchone()
            stats = get_stats(connection, module_id=inline_row["module_id"], review_only=False)

        matching_question = next(
            question for question in stats["questions"] if question["prompt"] == inline_row["prompt"]
        )
        self.assertIn("[_]", matching_question["prompt_preview"])
        self.assertNotIn("[blank]", matching_question["prompt_preview"])

    def test_api_quiz_stats_and_revision_flow(self) -> None:
        with self.build_client() as client:
            modules = client.get("/api/modules/tree")
            self.assertEqual(modules.status_code, 200)
            roots = modules.json()
            self.assertEqual(len(roots), 2)

            new_module = client.post(
                "/api/modules",
                json={
                    "title": "Microbiology",
                    "parent_id": roots[0]["id"],
                    "ui_copy": {
                        "question_label": "Question",
                        "answer_label": "Answer",
                        "stats_title": "Stats",
                        "review_title": "Review",
                    },
                },
            )
            self.assertEqual(new_module.status_code, 200)

            question = client.post(
                "/api/questions",
                json={
                    "module_id": new_module.json()["id"],
                    "prompt": "What kingdom includes bacteria?",
                    "question_type": "single_text",
                    "ranking": 4,
                    "review_flag": True,
                    "accepted_answers": [["bacteria", "bacterial kingdom"]],
                    "slot_prompts": [],
                    "segments": [],
                },
            )
            self.assertEqual(question.status_code, 200)
            question_id = question.json()["question_id"]

            revised = client.post(
                f"/api/questions/{question_id}/revisions",
                json={
                    "module_id": new_module.json()["id"],
                    "prompt": "What domain includes bacteria?",
                    "question_type": "single_text",
                    "ranking": 4,
                    "review_flag": True,
                    "accepted_answers": [["bacteria"]],
                    "slot_prompts": [],
                    "segments": [],
                    "reset_stats": True,
                },
            )
            self.assertEqual(revised.status_code, 200)

            review_flag = client.patch(
                f"/api/questions/{question_id}/review-flag",
                json={"review_flag": False},
            )
            self.assertEqual(review_flag.status_code, 200)
            self.assertFalse(review_flag.json()["review_flag"])

            session = client.post("/api/quiz-sessions", json={"module_id": None, "count": 3})
            self.assertEqual(session.status_code, 200)
            items = session.json()["items"]
            self.assertGreaterEqual(len(items), 1)
            self.assertIn("review_flag", items[0])

            first_item = items[0]
            submit = client.post(
                f"/api/quiz-sessions/{session.json()['id']}/items/{first_item['id']}/submit",
                json={"answers": ["tokyo"]},
            )
            self.assertEqual(submit.status_code, 200)
            self.assertIn("canonical_answers", submit.json())
            self.assertIn("score_earned", submit.json())
            self.assertIn("score_possible", submit.json())

            stats = client.get("/api/stats?review_only=true")
            self.assertEqual(stats.status_code, 200)
            stats_payload = stats.json()
            self.assertGreaterEqual(stats_payload["summary"]["reviewed_questions"], 0)
            self.assertIn("total_possible", stats_payload["summary"])
            self.assertTrue(all(question["review_flag"] for question in stats_payload["questions"]))


if __name__ == "__main__":
    unittest.main()
