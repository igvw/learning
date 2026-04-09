from __future__ import annotations

import random
import unittest

from backend.app.qml import parse_qml_line, render_prompt_and_answers
from backend.app.service.schedule import (
    _bucketed_question_selection,
    _eligible_quiz_candidates,
    _logical_bucket_label,
    _randomize_quiz_order,
    _schedule_snapshot_from_attempts,
)


class SchedulerUnitTests(unittest.TestCase):
    def test_qml_single_and_computed_questions_parse(self) -> None:
        single = parse_qml_line(
            line="What is the capital of Norway? [oslo | christiania]",
            module_id=1,
            rank=1,
        )
        computed = parse_qml_line(
            line="Patient needs $m=[1-10]*100$ mg. Solution strength is $v=[1-10]*10$ mg/ml. How much is needed? [$m/v$ ml]",
            module_id=1,
            rank=2,
        )

        self.assertEqual(single["question_type"], "single_text")
        self.assertEqual(single["accepted_answers"], [["oslo", "christiania"]])
        self.assertEqual(computed["question_type"], "computed_text")
        self.assertEqual(computed["accepted_answers"], [["$m/v$ ml"]])

    def test_computed_prompt_and_answers_resolve_once(self) -> None:
        prompt, answers = render_prompt_and_answers(
            prompt="Patient needs $m=[5-5]*100$ mg. Solution strength is $v=[4-4]*10$ mg/ml. How much is needed?",
            accepted_answers=[["$m/v$ ml"]],
            rng=random.Random(1),
        )

        self.assertEqual(
            prompt,
            "Patient needs 500 mg. Solution strength is 40 mg/ml. How much is needed?",
        )
        self.assertEqual(answers, [["12.5 ml"]])

    def test_quiz_order_is_randomized_after_selection(self) -> None:
        shuffled = _randomize_quiz_order(
            [
                {"question_id": 1},
                {"question_id": 2},
                {"question_id": 3},
                {"question_id": 4},
            ],
            rng=random.Random(7),
        )

        self.assertEqual([row["question_id"] for row in shuffled], [4, 2, 1, 3])

    def test_review_flagged_questions_are_excluded_from_quiz_candidates(self) -> None:
        eligible = _eligible_quiz_candidates(
            [
                {"question_id": 1, "review_flag": True},
                {"question_id": 2, "review_flag": False},
                {"question_id": 3},
            ]
        )

        self.assertEqual([row["question_id"] for row in eligible], [2, 3])

    def test_logical_bucket_uses_review_and_bucket_origin_before_hotness(self) -> None:
        self.assertEqual(
            _logical_bucket_label(
                bucket="hot1_sit_out",
                interval_step=None,
                bucket_origin_step=5,
                review_flag=False,
            ),
            "3d",
        )
        self.assertEqual(
            _logical_bucket_label(
                bucket="hot0",
                interval_step=None,
                bucket_origin_step=2,
                review_flag=True,
            ),
            "review",
        )

    def test_missed_question_stays_hot_in_next_quiz(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            }
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T12:05:00+00:00",
            latest_scored_session_id=10,
        )

        self.assertEqual(schedule["bucket"], "hot0")
        self.assertEqual(schedule["recovery_streak"], 0)

    def test_first_recovery_correct_enters_one_quiz_cooldown(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            }
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T12:15:00+00:00",
            latest_scored_session_id=11,
        )

        self.assertEqual(schedule["bucket"], "hot1_sit_out")
        self.assertEqual(schedule["recovery_streak"], 1)

    def test_hot1_becomes_eligible_after_one_intervening_quiz(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T12:20:00+00:00",
            latest_scored_session_id=12,
        )

        self.assertEqual(schedule["bucket"], "hot1")
        self.assertEqual(schedule["recovery_streak"], 1)

    def test_unseen_first_try_correct_moves_to_mastery(self) -> None:
        attempts = [
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            }
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T12:05:00+00:00",
            latest_scored_session_id=10,
        )

        self.assertEqual(schedule["bucket"], "mastery")
        self.assertIsNone(schedule["interval_step"])

    def test_second_recovery_correct_moves_to_first_bucket(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:30:00+00:00",
                "session_id": 13,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T12:35:00+00:00",
            latest_scored_session_id=13,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["recovery_streak"], 2)
        self.assertEqual(schedule["next_due_at"], "2026-04-05T13:30:00+00:00")
        self.assertEqual(schedule["interval_step"], 0)

    def test_bucket_miss_waits_one_quiz_before_retry(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:30:00+00:00",
                "session_id": 13,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T13:35:00+00:00",
                "session_id": 14,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T13:40:00+00:00",
            latest_scored_session_id=14,
        )

        self.assertEqual(schedule["bucket"], "bucket_retry_wait")
        self.assertEqual(schedule["interval_step"], 0)
        self.assertTrue(schedule["retry_pending"])

        eligible = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T14:00:00+00:00",
            latest_scored_session_id=15,
        )
        self.assertEqual(eligible["bucket"], "due_review")
        self.assertTrue(eligible["retry_pending"])

    def test_bucket_retry_correct_returns_to_original_bucket(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:30:00+00:00",
                "session_id": 13,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T13:35:00+00:00",
                "session_id": 14,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T14:35:00+00:00",
                "session_id": 16,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T14:40:00+00:00",
            latest_scored_session_id=16,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["interval_step"], 0)

    def test_bucket_retry_incorrect_then_hot_recovery_returns_to_original_bucket_after_one_failure(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:30:00+00:00",
                "session_id": 13,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T13:35:00+00:00",
                "session_id": 14,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T14:35:00+00:00",
                "session_id": 16,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T15:00:00+00:00",
                "session_id": 17,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T15:30:00+00:00",
                "session_id": 19,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T15:35:00+00:00",
            latest_scored_session_id=19,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["interval_step"], 0)

    def test_bucket_retry_multiple_failures_drop_one_bucket(self) -> None:
        attempts = [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:30:00+00:00",
                "session_id": 13,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T13:35:00+00:00",
                "session_id": 14,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T16:40:00+00:00",
                "session_id": 20,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T17:40:00+00:00",
                "session_id": 22,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T18:00:00+00:00",
                "session_id": 23,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T18:20:00+00:00",
                "session_id": 24,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T18:40:00+00:00",
                "session_id": 25,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T19:00:00+00:00",
                "session_id": 27,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T19:05:00+00:00",
            latest_scored_session_id=27,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["interval_step"], 0)

    def test_selector_does_not_serve_hot1_sit_out(self) -> None:
        selected = _bucketed_question_selection(
            [
                {
                    "question_id": 1,
                    "bucket": "hot1_sit_out",
                    "last_incorrect_at": "2026-04-05T12:00:00+00:00",
                    "recovery_streak": 1,
                    "rank": 1,
                },
                {
                    "question_id": 2,
                    "bucket": "unseen",
                    "rank": 2,
                },
            ],
            count=2,
            now="2026-04-05T12:10:00+00:00",
        )

        self.assertEqual([row["question_id"] for row in selected], [2])

    def test_selector_prioritizes_hot0_then_hot1_then_due_then_unseen(self) -> None:
        selected = _bucketed_question_selection(
            [
                {
                    "question_id": 1,
                    "bucket": "due_review",
                    "interval_step": 0,
                    "next_due_at": "2026-04-05T10:00:00+00:00",
                    "retry_pending": False,
                    "rank": 4,
                },
                {
                    "question_id": 2,
                    "bucket": "hot1",
                    "last_incorrect_at": "2026-04-05T12:00:00+00:00",
                    "recovery_streak": 1,
                    "rank": 2,
                },
                {
                    "question_id": 3,
                    "bucket": "hot0",
                    "last_incorrect_at": "2026-04-05T12:00:00+00:00",
                    "recovery_streak": 0,
                    "rank": 3,
                    "last_session_id": 10,
                    "latest_scored_session_id": 10,
                },
                {
                    "question_id": 4,
                    "bucket": "unseen",
                    "rank": 1,
                },
            ],
            count=4,
            now="2026-04-05T12:10:00+00:00",
        )

        self.assertEqual([row["question_id"] for row in selected], [3, 2, 1, 4])

    def test_selector_prioritizes_due_review_questions_over_unseen(self) -> None:
        selected = _bucketed_question_selection(
            [
                {
                    "question_id": 1,
                    "bucket": "unseen",
                    "rank": 1,
                },
                {
                    "question_id": 2,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T15:00:00+00:00",
                    "interval_step": 1,
                    "retry_pending": False,
                    "rank": 4,
                },
            ],
            count=1,
            now="2026-04-05T12:10:00+00:00",
        )

        self.assertEqual([row["question_id"] for row in selected], [2])

    def test_selector_orders_due_review_questions_from_earliest_stage_to_latest(self) -> None:
        selected = _bucketed_question_selection(
            [
                {
                    "question_id": 1,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T16:00:00+00:00",
                    "interval_step": 3,
                    "retry_pending": False,
                    "rank": 1,
                },
                {
                    "question_id": 2,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T18:00:00+00:00",
                    "interval_step": 0,
                    "retry_pending": False,
                    "rank": 5,
                },
                {
                    "question_id": 3,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T15:00:00+00:00",
                    "interval_step": 1,
                    "retry_pending": False,
                    "rank": 2,
                },
            ],
            count=3,
            now="2026-04-05T12:10:00+00:00",
        )

        self.assertEqual([row["question_id"] for row in selected], [2, 3, 1])

    def test_selector_does_not_serve_mastery_as_fallback(self) -> None:
        selected = _bucketed_question_selection(
            [
                {
                    "question_id": 1,
                    "bucket": "mastery",
                    "rank": 1,
                }
            ],
            count=1,
            now="2026-04-05T12:10:00+00:00",
        )

        self.assertEqual(selected, [])
