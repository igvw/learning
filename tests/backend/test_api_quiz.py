from test_support import PostgresBackendTestCase


class QuizApiTests(PostgresBackendTestCase):
    def test_quiz_flow_is_user_scoped(self) -> None:
        user = self.create_user()

        unauthenticated = self.client.post(
            "/api/quiz-sessions",
            json={"module_id": 5, "count": 2},
        )
        self.assertEqual(unauthenticated.status_code, 400)
        self.assertEqual(unauthenticated.json()["detail"], "X-User-Id header is required.")

        session = self.start_quiz_session(user["id"], 5, 2)
        self.assertEqual(session["module_id"], 5)
        self.assertEqual(len(session["items"]), 2)

        first_item = session["items"][0]
        submit_payload = self.submit_quiz_item(user["id"], session["id"], first_item["id"], ["nairobi"])
        self.assertEqual(submit_payload["score_possible"], 1.0)

        stats_payload = self.get_stats_payload(user["id"], 5)
        self.assertGreaterEqual(stats_payload["summary"]["total_attempts"], 1)

    def test_review_flagged_questions_do_not_reappear_in_quiz(self) -> None:
        user = self.create_user()

        flagged_question_id = self.get_stats_payload(user["id"], 5)["questions"][0]["question_id"]
        self.set_review_flag(user["id"], flagged_question_id, True)

        session = self.start_quiz_session(user["id"], 5, 10)
        returned_ids = [item["question_id"] for item in session["items"]]
        self.assertNotIn(flagged_question_id, returned_ids)

    def test_unseen_miss_then_correct_reappears_in_next_quiz_without_sit_out(self) -> None:
        norwegian = self.create_module_record("Norwegian Retry")
        weekdays = self.create_module_record("Weekdays Retry", norwegian["id"])
        first_question_id = self.create_question_record(
            weekdays["id"],
            "mandag",
            [["Monday"]],
            rank=1,
        )["question_id"]
        self.create_question_record(
            weekdays["id"],
            "tirsdag",
            [["Tuesday"]],
            rank=2,
        )

        user = self.create_user("alice-unseen-retry", "Alice Unseen Retry")

        first_session = self.start_quiz_session(user["id"], weekdays["id"], 1)
        first_item = first_session["items"][0]
        self.assertEqual(first_item["question_id"], first_question_id)

        first_submit = self.submit_quiz_item(user["id"], first_session["id"], first_item["id"], ["wrong"])
        self.assertFalse(first_submit["is_correct"])

        second_session = self.start_quiz_session(user["id"], weekdays["id"], 1)
        second_item = second_session["items"][0]
        self.assertEqual(second_item["question_id"], first_question_id)

        second_submit = self.submit_quiz_item(user["id"], second_session["id"], second_item["id"], ["monday"])
        self.assertTrue(second_submit["is_correct"])

        third_session = self.start_quiz_session(user["id"], weekdays["id"], 1)
        self.assertEqual(third_session["items"][0]["question_id"], first_question_id)

    def test_answer_checking_is_case_insensitive(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        weekdays = self.create_module_record("Weekdays", norwegian["id"])
        question_id = self.create_question_record(
            weekdays["id"],
            "lørdag",
            [["Saturday"]],
        )["question_id"]

        user = self.create_user()
        session = self.start_quiz_session(user["id"], weekdays["id"], 1)
        item = session["items"][0]
        self.assertEqual(item["question_id"], question_id)

        submit_payload = self.submit_quiz_item(user["id"], session["id"], item["id"], ["saturday"])
        self.assertTrue(submit_payload["is_correct"])
        self.assertEqual(submit_payload["score_earned"], 1.0)
        self.assertEqual(submit_payload["canonical_answers"], ["Saturday"])

        stats_payload = self.get_stats_payload(user["id"], weekdays["id"])
        self.assertEqual(len(stats_payload["questions"]), 1)
        self.assertEqual(stats_payload["questions"][0]["question_id"], question_id)
        self.assertEqual(stats_payload["questions"][0]["attempts"], 1)
        self.assertEqual(stats_payload["questions"][0]["correct_percentage"], 1.0)

    def test_quiz_submission_returns_default_and_alternative_feedback(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        weekdays = self.create_module_record("Weekdays", norwegian["id"])
        question_id = self.create_question_record(
            weekdays["id"],
            "lørdag",
            [["Saturday", "Sat"]],
        )["question_id"]

        user = self.create_user("alice-alt", "Alice Alt")
        session = self.start_quiz_session(user["id"], weekdays["id"], 1)
        item = session["items"][0]
        self.assertEqual(item["question_id"], question_id)

        submit_payload = self.submit_quiz_item(user["id"], session["id"], item["id"], ["sat"])
        self.assertTrue(submit_payload["is_correct"])
        self.assertEqual(submit_payload["canonical_answers"], ["Saturday / Sat"])
        self.assertEqual(submit_payload["default_answers"], ["Saturday"])
        self.assertEqual(submit_payload["accepted_answer_groups"], [["Saturday", "Sat"]])
        self.assertEqual(submit_payload["matched_default_answers"], [False])

    def test_quiz_submission_marks_default_matches_for_unordered_multi(self) -> None:
        geography = self.create_module_record("Geography Alt")
        capitals = self.create_module_record("Capitals Alt", geography["id"])
        question_id = self.create_question_record(
            capitals["id"],
            "Name the capitals of Norway and Sweden.",
            [["Oslo"], ["Stockholm", "Sthlm"]],
            question_type="multi_text",
        )["question_id"]

        user = self.create_user("alice-multi", "Alice Multi")
        session = self.start_quiz_session(user["id"], capitals["id"], 1)
        item = session["items"][0]
        self.assertEqual(item["question_id"], question_id)

        submit_payload = self.submit_quiz_item(user["id"], session["id"], item["id"], ["sthlm", "oslo"])
        self.assertTrue(submit_payload["is_correct"])
        self.assertEqual(submit_payload["score_earned"], 1.0)
        self.assertEqual(submit_payload["default_answers"], ["Oslo", "Stockholm"])
        self.assertEqual(submit_payload["accepted_answer_groups"], [["Oslo"], ["Stockholm", "Sthlm"]])
        self.assertEqual(submit_payload["matched_default_answers"], [False, True])
