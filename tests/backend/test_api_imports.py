from backend.app.database import get_connection
from test_support import PostgresBackendTestCase


class ImportApiTests(PostgresBackendTestCase):
    def test_same_tree_reimport_moves_question_and_preserves_progress(self) -> None:
        module_ids = self.create_module_tree()
        question_id = self.create_question_record(
            module_ids["source_a"],
            "hund",
            [["dog"]],
        )["question_id"]

        user = self.create_user()
        session = self.start_quiz_session(user["id"], module_ids["source_a"], 1)
        item = session["items"][0]
        self.submit_quiz_item(user["id"], session["id"], item["id"], ["dog"])
        self.set_review_flag(user["id"], question_id, True)

        validate_payload = self.validate_import_payload(module_ids["target"], qml_text="hund [dog]")
        self.assertEqual(validate_payload["review_rows"][0]["status"], "info")
        self.assertFalse(validate_payload["review_rows"][0]["blocking"])
        self.assertEqual(validate_payload["committable_row_numbers"], [1])

        commit_payload = self.commit_import_payload(
            module_ids["target"],
            [{"row_number": 1, "qml_line": "hund [dog]"}],
        )
        self.assertTrue(commit_payload["committed"])

        source_stats = self.get_stats_payload(user["id"], module_ids["source_a"])
        self.assertEqual(source_stats["questions"], [])

        target_stats = self.get_stats_payload(user["id"], module_ids["target"])
        self.assertEqual(len(target_stats["questions"]), 1)
        self.assertEqual(target_stats["questions"][0]["question_id"], question_id)
        self.assertEqual(target_stats["questions"][0]["attempts"], 1)
        self.assertFalse(target_stats["questions"][0]["review_flag"])

    def test_exact_duplicate_in_target_leaf_is_omitted_from_review_rows(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        self.create_question_record(target["id"], "år", [["year"]])

        validate_payload = self.validate_import_payload(target["id"], qml_text="år [year]")
        self.assertEqual(validate_payload["exact_duplicate_count"], 1)
        self.assertEqual(validate_payload["committable_row_numbers"], [])
        self.assertEqual(validate_payload["review_rows"], [])
        self.assertFalse(validate_payload["ready_to_commit"])

        commit_payload = self.commit_import_payload(
            target["id"],
            [{"row_number": 1, "qml_line": "år [year]"}],
        )
        self.assertFalse(commit_payload["committed"])
        self.assertEqual(commit_payload["exact_duplicate_count"], 1)
        self.assertEqual(commit_payload["committable_row_numbers"], [])

    def test_same_leaf_duplicate_with_changed_answers_revises_existing_question(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        question_id = self.create_question_record(target["id"], "mot", [["against"]])["question_id"]

        user = self.create_user()
        session = self.start_quiz_session(user["id"], target["id"], 1)
        item = session["items"][0]
        self.submit_quiz_item(user["id"], session["id"], item["id"], ["against"])
        self.set_review_flag(user["id"], question_id, True)

        validate_payload = self.validate_import_payload(target["id"], qml_text="mot [against | toward]")
        self.assertEqual(validate_payload["review_rows"][0]["status"], "duplicate")
        self.assertFalse(validate_payload["review_rows"][0]["blocking"])
        self.assertEqual(validate_payload["review_rows"][0]["matched_questions"][0]["question_id"], question_id)

        commit_payload = self.commit_import_payload(
            target["id"],
            [{"row_number": 1, "qml_line": "mot [against | toward]"}],
        )
        self.assertTrue(commit_payload["committed"])

        target_stats = self.get_stats_payload(user["id"], target["id"])
        self.assertEqual(len(target_stats["questions"]), 1)
        self.assertEqual(target_stats["questions"][0]["question_id"], question_id)
        self.assertEqual(target_stats["questions"][0]["attempts"], 1)
        self.assertFalse(target_stats["questions"][0]["review_flag"])
        self.assertEqual(target_stats["questions"][0]["accepted_answers"], [["against", "toward"]])

    def test_same_leaf_exact_noop_duplicate_has_no_side_effects(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        question_id = self.create_question_record(target["id"], "mot", [["against"]])["question_id"]

        user = self.create_user()
        session = self.start_quiz_session(user["id"], target["id"], 1)
        item = session["items"][0]
        self.submit_quiz_item(user["id"], session["id"], item["id"], ["against"])
        self.set_review_flag(user["id"], question_id, True)

        commit_payload = self.commit_import_payload(
            target["id"],
            [{"row_number": 1, "qml_line": "mot [against]"}],
        )
        self.assertFalse(commit_payload["committed"])
        self.assertEqual(commit_payload["exact_duplicate_count"], 1)
        self.assertEqual(commit_payload["committed_count"], 0)

        target_stats = self.get_stats_payload(user["id"], target["id"])
        self.assertEqual(len(target_stats["questions"]), 1)
        self.assertEqual(target_stats["questions"][0]["question_id"], question_id)
        self.assertEqual(target_stats["questions"][0]["attempts"], 1)
        self.assertTrue(target_stats["questions"][0]["review_flag"])
        self.assertEqual(target_stats["questions"][0]["accepted_answers"], [["against"]])

    def test_same_upload_changed_duplicate_blocks_commit_until_resolved(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])

        validate_payload = self.validate_import_payload(
            target["id"],
            rows=[
                {"row_number": 1, "qml_line": "selv [self]"},
                {"row_number": 2, "qml_line": "selv [self | even]"},
            ],
        )
        self.assertFalse(validate_payload["ready_to_commit"])
        self.assertEqual(validate_payload["exact_duplicate_count"], 0)
        self.assertEqual(len(validate_payload["review_rows"]), 1)
        self.assertEqual(validate_payload["review_rows"][0]["status"], "duplicate")
        self.assertTrue(validate_payload["review_rows"][0]["blocking"])
        self.assertEqual(validate_payload["review_rows"][0]["matched_questions"][0]["module_full_slug"], "Earlier upload row 1")

        commit_payload = self.commit_import_payload(
            target["id"],
            [
                {"row_number": 1, "qml_line": "selv [self]"},
                {"row_number": 2, "qml_line": "selv [self | even]"},
            ],
        )
        self.assertFalse(commit_payload["committed"])

    def test_same_tree_multi_match_returns_blocking_conflict(self) -> None:
        module_ids = self.create_module_tree()
        first_question_id = self.create_question_record(
            module_ids["source_a"],
            "hund",
            [["dog"]],
        )["question_id"]
        second_question_id = self.create_question_record(
            module_ids["source_b"],
            "hund",
            [["canine"]],
        )["question_id"]

        user = self.create_user("bob", "Bob")
        session = self.start_quiz_session(user["id"], module_ids["source_b"], 1)
        item = session["items"][0]
        self.submit_quiz_item(user["id"], session["id"], item["id"], ["wrong"])
        self.set_review_flag(user["id"], first_question_id, True)
        self.set_review_flag(user["id"], second_question_id, True)

        validate_payload = self.validate_import_payload(module_ids["target"], qml_text="hund [dog | canine | pooch]")
        self.assertEqual(validate_payload["review_rows"][0]["status"], "conflict")
        self.assertTrue(validate_payload["review_rows"][0]["blocking"])
        self.assertEqual(len(validate_payload["review_rows"][0]["matched_questions"]), 2)
        self.assertFalse(validate_payload["ready_to_commit"])

        commit_payload = self.commit_import_payload(
            module_ids["target"],
            [{"row_number": 1, "qml_line": "hund [dog | canine | pooch]"}],
        )
        self.assertFalse(commit_payload["committed"])

        target_stats = self.get_stats_payload(user["id"], module_ids["target"])
        self.assertEqual(target_stats["questions"], [])

        with get_connection(self.database_url) as connection:
            question_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM questions WHERE prompt = ? ORDER BY id ASC",
                    ("hund",),
                ).fetchall()
            ]
        self.assertEqual(question_ids, [first_question_id, second_question_id])
