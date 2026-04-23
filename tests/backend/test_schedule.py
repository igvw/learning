import random
import unittest
from datetime import timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from backend.app.qml import parse_qml_line
from backend.app.service.text import title_from_slug
from backend.app.service.schedule import (
    _bucketed_question_selection,
    _eligible_quiz_candidates,
    _logical_bucket_label,
    _randomize_quiz_order,
    _schedule_snapshot_from_attempts,
)
from backend.app.service.time_utils import schedule_due_at

FIXED_LADDER_ATTEMPTS = [
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
        "answered_at": "2026-04-05T13:40:00+00:00",
        "session_id": 14,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-04-05T16:50:00+00:00",
        "session_id": 15,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-04-05T23:00:00+00:00",
        "session_id": 16,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-04-06T12:00:00+00:00",
        "session_id": 17,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-04-07T12:00:00+00:00",
        "session_id": 18,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-04-10T12:00:00+00:00",
        "session_id": 19,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-04-17T12:00:00+00:00",
        "session_id": 20,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-05-01T12:00:00+00:00",
        "session_id": 21,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-05-31T12:00:00+00:00",
        "session_id": 22,
    },
    {
        "score_earned": 1.0,
        "score_possible": 1.0,
        "answered_at": "2026-07-30T12:00:00+00:00",
        "session_id": 23,
    },
]


class SchedulerUnitTests(unittest.TestCase):
    def test_title_from_slug_capitalizes_each_word(self) -> None:
        self.assertEqual(title_from_slug("animals_to_english"), "Animals To English")
        self.assertEqual(title_from_slug("iv_med_calc"), "Iv Med Calc")

    def test_qml_single_and_bundle_questions_parse(self) -> None:
        single = parse_qml_line(
            line="What is the capital of Norway? [oslo | christiania]",
            module_id=1,
            rank=1,
        )
        bundle = parse_qml_line(
            line="{Patient needs {} mg. Solution strength is {} mg/ml. How much is needed? []\n {500} {40} [12.5 ml]}",
            module_id=1,
            rank=2,
        )

        self.assertEqual(single["question_type"], "single_text")
        self.assertEqual(single["accepted_answers"], [["oslo", "christiania"]])
        self.assertEqual(bundle["question_type"], "bundle")
        self.assertEqual(bundle["prompt"], "Patient needs {} mg. Solution strength is {} mg/ml. How much is needed? []")
        self.assertEqual(bundle["bundle_variants"][0]["prompt_values"], ["500", "40"])
        self.assertEqual(bundle["bundle_variants"][0]["accepted_answers"], ["12.5 ml"])

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
                bucket_origin_step=8,
                review_flag=False,
            ),
            "30d",
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
        self.assertEqual(
            _logical_bucket_label(
                bucket="cooling",
                interval_step=9,
                bucket_origin_step=None,
                review_flag=False,
            ),
            "60d",
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

    def test_non_unseen_hot1_still_enters_one_quiz_cooldown(self) -> None:
        attempts = [
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:00:00+00:00",
                "session_id": 10,
            },
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:10:00+00:00",
                "session_id": 11,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T12:20:00+00:00",
                "session_id": 12,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T12:25:00+00:00",
            latest_scored_session_id=12,
        )

        self.assertEqual(schedule["bucket"], "hot1_sit_out")
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

    def test_day_scale_bucket_due_times_snap_to_midnight_by_default(self) -> None:
        schedule = _schedule_snapshot_from_attempts(
            FIXED_LADDER_ATTEMPTS[:7],
            now="2026-04-06T12:05:00+00:00",
            latest_scored_session_id=17,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["interval_step"], 4)
        self.assertEqual(schedule["next_due_at"], "2026-04-07T00:00:00+00:00")

    def test_day_scale_bucket_becomes_due_just_after_midnight(self) -> None:
        schedule = _schedule_snapshot_from_attempts(
            FIXED_LADDER_ATTEMPTS[:7],
            now="2026-04-07T00:05:00+00:00",
            latest_scored_session_id=17,
        )

        self.assertEqual(schedule["bucket"], "due_review")
        self.assertEqual(schedule["interval_step"], 4)
        self.assertEqual(schedule["next_due_at"], "2026-04-07T00:00:00+00:00")

    def test_fixed_bucket_ladder_extends_from_14d_to_30d_to_60d_then_mastery(self) -> None:
        thirty_day = _schedule_snapshot_from_attempts(
            FIXED_LADDER_ATTEMPTS[:11],
            now="2026-05-01T12:05:00+00:00",
            latest_scored_session_id=21,
        )
        self.assertEqual(thirty_day["bucket"], "cooling")
        self.assertEqual(thirty_day["interval_step"], 8)
        self.assertEqual(thirty_day["next_due_at"], "2026-05-31T00:00:00+00:00")
        self.assertEqual(
            _logical_bucket_label(
                bucket=thirty_day["bucket"],
                interval_step=thirty_day["interval_step"],
                bucket_origin_step=thirty_day.get("bucket_origin_step"),
                review_flag=False,
            ),
            "30d",
        )

        sixty_day = _schedule_snapshot_from_attempts(
            FIXED_LADDER_ATTEMPTS[:12],
            now="2026-05-31T12:05:00+00:00",
            latest_scored_session_id=22,
        )
        self.assertEqual(sixty_day["bucket"], "cooling")
        self.assertEqual(sixty_day["interval_step"], 9)
        self.assertEqual(sixty_day["next_due_at"], "2026-07-30T00:00:00+00:00")
        self.assertEqual(
            _logical_bucket_label(
                bucket=sixty_day["bucket"],
                interval_step=sixty_day["interval_step"],
                bucket_origin_step=sixty_day.get("bucket_origin_step"),
                review_flag=False,
            ),
            "60d",
        )

        mastery = _schedule_snapshot_from_attempts(
            FIXED_LADDER_ATTEMPTS,
            now="2026-07-30T12:05:00+00:00",
            latest_scored_session_id=23,
        )
        self.assertEqual(mastery["bucket"], "mastery")
        self.assertIsNone(mastery["interval_step"])
        self.assertIsNone(mastery["next_due_at"])

    def test_lowest_bucket_miss_reenters_hot_recovery_immediately(self) -> None:
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

        self.assertEqual(schedule["bucket"], "hot0")
        self.assertIsNone(schedule["interval_step"])
        self.assertEqual(schedule["bucket_origin_step"], 0)
        self.assertEqual(schedule["last_session_id"], 14)

    def test_lowest_bucket_miss_is_selected_again_in_next_quiz(self) -> None:
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

        selected = _bucketed_question_selection(
            [
                {
                    "question_id": 1,
                    "rank": 5,
                    "latest_scored_session_id": 14,
                    **schedule,
                },
                {
                    "question_id": 2,
                    "bucket": "unseen",
                    "rank": 1,
                },
            ],
            count=1,
            now="2026-04-05T13:40:00+00:00",
        )

        self.assertEqual([row["question_id"] for row in selected], [1])

    def test_higher_bucket_miss_reenters_hot_recovery_immediately(self) -> None:
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
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T16:45:00+00:00",
            latest_scored_session_id=20,
        )

        self.assertEqual(schedule["bucket"], "hot0")
        self.assertIsNone(schedule["interval_step"])
        self.assertEqual(schedule["bucket_origin_step"], 1)
        self.assertEqual(schedule["last_session_id"], 20)

    def test_thirty_day_miss_reenters_hot_recovery_immediately(self) -> None:
        attempts = FIXED_LADDER_ATTEMPTS[:11] + [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-05-31T12:10:00+00:00",
                "session_id": 24,
            }
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-05-31T12:15:00+00:00",
            latest_scored_session_id=24,
        )

        self.assertEqual(schedule["bucket"], "hot0")
        self.assertIsNone(schedule["interval_step"])
        self.assertEqual(schedule["bucket_origin_step"], 8)

    def test_sixty_day_miss_reenters_hot_recovery_immediately(self) -> None:
        attempts = FIXED_LADDER_ATTEMPTS[:12] + [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-07-30T12:10:00+00:00",
                "session_id": 24,
            }
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-07-30T12:15:00+00:00",
            latest_scored_session_id=24,
        )

        self.assertEqual(schedule["bucket"], "hot0")
        self.assertIsNone(schedule["interval_step"])
        self.assertEqual(schedule["bucket_origin_step"], 9)

    def test_bucket_recovery_with_one_wrong_returns_to_original_bucket(self) -> None:
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
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T17:40:00+00:00",
                "session_id": 22,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T18:00:00+00:00",
                "session_id": 24,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T18:05:00+00:00",
            latest_scored_session_id=24,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["interval_step"], 1)

    def test_bucket_recovery_with_multiple_wrongs_drops_one_bucket(self) -> None:
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
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-05T18:40:00+00:00",
                "session_id": 25,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-05T18:45:00+00:00",
            latest_scored_session_id=25,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["interval_step"], 0)

    def test_bucket_recovery_back_to_one_day_bucket_uses_midnight_due_time(self) -> None:
        attempts = FIXED_LADDER_ATTEMPTS[:7] + [
            {
                "score_earned": 0.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-07T00:10:00+00:00",
                "session_id": 18,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-07T00:20:00+00:00",
                "session_id": 19,
            },
            {
                "score_earned": 1.0,
                "score_possible": 1.0,
                "answered_at": "2026-04-07T09:00:00+00:00",
                "session_id": 20,
            },
        ]

        schedule = _schedule_snapshot_from_attempts(
            attempts,
            now="2026-04-07T09:05:00+00:00",
            latest_scored_session_id=20,
        )

        self.assertEqual(schedule["bucket"], "cooling")
        self.assertEqual(schedule["interval_step"], 4)
        self.assertEqual(schedule["next_due_at"], "2026-04-08T00:00:00+00:00")

    def test_day_scale_midnight_due_respects_dst_in_configured_schedule_timezone(self) -> None:
        with patch.dict("os.environ", {"LEARNING_APP_SCHEDULE_TIMEZONE": "Europe/Oslo"}, clear=True):
            due_at = schedule_due_at(
                "2026-03-28T23:30:00+00:00",
                timedelta(days=1),
                timezone=ZoneInfo("Europe/Oslo"),
            )

        self.assertEqual(due_at, "2026-03-30T00:00:00+02:00")

    def test_bucket_recovery_multiple_failures_still_drop_one_bucket(self) -> None:
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

    def test_selector_serves_hot1_after_one_intervening_quiz_before_due_and_unseen(self) -> None:
        schedule = _schedule_snapshot_from_attempts(
            [
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
            ],
            now="2026-04-05T12:15:00+00:00",
            latest_scored_session_id=12,
        )

        selected = _bucketed_question_selection(
            [
                {
                    "question_id": 1,
                    "rank": 3,
                    "latest_scored_session_id": 11,
                    **schedule,
                },
                {
                    "question_id": 2,
                    "bucket": "due_review",
                    "interval_step": 0,
                    "next_due_at": "2026-04-05T11:00:00+00:00",
                    "rank": 2,
                },
                {
                    "question_id": 3,
                    "bucket": "unseen",
                    "rank": 1,
                },
            ],
            count=1,
            now="2026-04-05T12:15:00+00:00",
        )

        self.assertEqual([row["question_id"] for row in selected], [1])

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
                    "rank": 1,
                },
                {
                    "question_id": 2,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T18:00:00+00:00",
                    "interval_step": 0,
                    "rank": 5,
                },
                {
                    "question_id": 3,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T15:00:00+00:00",
                    "interval_step": 1,
                    "rank": 2,
                },
                {
                    "question_id": 4,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T12:30:00+00:00",
                    "interval_step": 9,
                    "rank": 3,
                },
                {
                    "question_id": 5,
                    "bucket": "due_review",
                    "next_due_at": "2026-04-05T12:15:00+00:00",
                    "interval_step": 8,
                    "rank": 4,
                },
            ],
            count=5,
            now="2026-04-05T12:10:00+00:00",
        )

        self.assertEqual([row["question_id"] for row in selected], [2, 3, 1, 5, 4])

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
