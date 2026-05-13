from backend.app.database import get_connection
from test_support import PostgresBackendTestCase


def plain_import_entry(start_line: int, qml_text: str) -> dict[str, object]:
    return {
        "start_line": start_line,
        "end_line": start_line,
        "entry_kind": "plain",
        "qml_text": qml_text,
    }


class ImportApiTests(PostgresBackendTestCase):
    def test_import_routes_require_admin_authentication(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        validate_payload = {"module_id": target["id"], "qml_text": "hund [dog]"}
        commit_payload = {"module_id": target["id"], "rows": [plain_import_entry(1, "hund [dog]")]}

        validate_unauthenticated = self.client.post("/api/question-imports/validate", json=validate_payload)
        self.assertEqual(validate_unauthenticated.status_code, 401)
        self.assertEqual(validate_unauthenticated.json()["detail"], "Authentication is required.")

        commit_unauthenticated = self.client.post("/api/question-imports/commit", json=commit_payload)
        self.assertEqual(commit_unauthenticated.status_code, 401)
        self.assertEqual(commit_unauthenticated.json()["detail"], "Authentication is required.")

        user = self.create_user()
        validate_user = self.client.post(
            "/api/question-imports/validate",
            json=validate_payload,
            headers=self.user_headers(int(user["id"])),
        )
        self.assertEqual(validate_user.status_code, 403)
        self.assertEqual(validate_user.json()["detail"], "Admin access is required.")

        commit_user = self.client.post(
            "/api/question-imports/commit",
            json=commit_payload,
            headers=self.user_headers(int(user["id"])),
        )
        self.assertEqual(commit_user.status_code, 403)
        self.assertEqual(commit_user.json()["detail"], "Admin access is required.")

    def test_import_routes_reject_legacy_line_only_rows(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])

        validate_response = self.client.post(
            "/api/question-imports/validate",
            json={"module_id": target["id"], "rows": [{"row_number": 1, "qml_line": "hund [dog]"}]},
            headers=self.admin_headers,
        )
        self.assertEqual(validate_response.status_code, 422)

        commit_response = self.client.post(
            "/api/question-imports/commit",
            json={"module_id": target["id"], "rows": [{"row_number": 1, "qml_line": "hund [dog]"}]},
            headers=self.admin_headers,
        )
        self.assertEqual(commit_response.status_code, 422)

    def test_same_tree_reimport_moves_question_and_preserves_progress(self) -> None:
        module_ids = self.create_module_tree()
        self.create_question_record(module_ids["target"], "først", [["first"]], rank=1)
        self.create_question_record(module_ids["target"], "andre", [["second"]], rank=2)
        question_id = self.create_question_record(
            module_ids["source_a"],
            "hund",
            [["dog"]],
            rank=1,
        )["question_id"]
        self.create_question_record(module_ids["source_a"], "katt", [["cat"]], rank=2)

        user = self.create_user()
        session = self.start_quiz_session(user["id"], module_ids["source_a"], 1)
        item = session["items"][0]
        self.submit_quiz_item(user["id"], session["id"], item["id"], ["dog"])

        validate_payload = self.validate_import_payload(module_ids["target"], qml_text="hund [dog]")
        self.assertEqual(validate_payload["review_rows"][0]["status"], "info")
        self.assertFalse(validate_payload["review_rows"][0]["blocking"])
        self.assertEqual(validate_payload["committable_start_lines"], [1])

        commit_payload = self.commit_import_payload(
            module_ids["target"],
            [plain_import_entry(1, "hund [dog]")],
        )
        self.assertTrue(commit_payload["committed"])

        source_stats = self.get_stats_payload(user["id"], module_ids["source_a"])
        self.assertEqual(len(source_stats["questions"]), 1)
        self.assertEqual(source_stats["questions"][0]["prompt"], "katt")
        self.assertEqual(source_stats["questions"][0]["rank"], 2)

        target_stats = self.get_stats_payload(user["id"], module_ids["target"])
        self.assertEqual(len(target_stats["questions"]), 3)
        moved_question = next(question for question in target_stats["questions"] if question["question_id"] == question_id)
        self.assertEqual(moved_question["attempts"], 1)

        with get_connection(self.database_url) as connection:
            target_prompts = [
                (row["prompt"], row["rank"])
                for row in connection.execute(
                    "SELECT prompt, rank FROM questions WHERE module_id = ? ORDER BY rank ASC, id ASC",
                    (module_ids["target"],),
                ).fetchall()
            ]
            source_prompts = [
                (row["prompt"], row["rank"])
                for row in connection.execute(
                    "SELECT prompt, rank FROM questions WHERE module_id = ? ORDER BY rank ASC, id ASC",
                    (module_ids["source_a"],),
                ).fetchall()
            ]
        self.assertEqual(target_prompts, [("først", 1), ("andre", 2), ("hund", 3)])
        self.assertEqual(source_prompts, [("katt", 2)])

    def test_new_imported_rows_append_after_existing_questions_in_upload_order(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        self.create_question_record(target["id"], "alfa", [["alpha"]], rank=1)
        self.create_question_record(target["id"], "beta", [["beta"]], rank=2)

        commit_payload = self.commit_import_payload(
            target["id"],
            [
                plain_import_entry(10, "gamma [gamma]"),
                plain_import_entry(20, "delta [delta]"),
            ],
        )
        self.assertTrue(commit_payload["committed"])

        with get_connection(self.database_url) as connection:
            prompts = [
                (row["prompt"], row["rank"])
                for row in connection.execute(
                    "SELECT prompt, rank FROM questions WHERE module_id = ? ORDER BY rank ASC, id ASC",
                    (target["id"],),
                ).fetchall()
            ]
        self.assertEqual(prompts, [("alfa", 1), ("beta", 2), ("gamma", 3), ("delta", 4)])

    def test_exact_duplicate_in_target_leaf_is_omitted_from_review_rows(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        self.create_question_record(target["id"], "år", [["year"]])

        validate_payload = self.validate_import_payload(target["id"], qml_text="år [year]")
        self.assertEqual(validate_payload["exact_duplicate_count"], 1)
        self.assertEqual(validate_payload["committable_start_lines"], [])
        self.assertEqual(validate_payload["review_rows"], [])
        self.assertFalse(validate_payload["ready_to_commit"])

        commit_payload = self.commit_import_payload(
            target["id"],
            [plain_import_entry(1, "år [year]")],
        )
        self.assertFalse(commit_payload["committed"])
        self.assertEqual(commit_payload["exact_duplicate_count"], 1)
        self.assertEqual(commit_payload["committable_start_lines"], [])

    def test_same_leaf_duplicate_with_changed_answers_revises_existing_question(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        question_id = self.create_question_record(target["id"], "mot", [["against"]])["question_id"]

        user = self.create_user()
        session = self.start_quiz_session(user["id"], target["id"], 1)
        item = session["items"][0]
        self.submit_quiz_item(user["id"], session["id"], item["id"], ["against"])

        validate_payload = self.validate_import_payload(target["id"], qml_text="mot [against | toward]")
        self.assertEqual(validate_payload["review_rows"][0]["status"], "duplicate")
        self.assertFalse(validate_payload["review_rows"][0]["blocking"])
        self.assertEqual(validate_payload["review_rows"][0]["matched_questions"][0]["question_id"], question_id)

        commit_payload = self.commit_import_payload(
            target["id"],
            [plain_import_entry(1, "mot [against | toward]")],
        )
        self.assertTrue(commit_payload["committed"])

        target_stats = self.get_stats_payload(user["id"], target["id"])
        self.assertEqual(len(target_stats["questions"]), 1)
        replacement_id = target_stats["questions"][0]["question_id"]
        self.assertNotEqual(replacement_id, question_id)
        self.assertEqual(target_stats["questions"][0]["attempts"], 1)
        self.assertEqual(target_stats["questions"][0]["accepted_answers"], [["against", "toward"]])
        self.assertEqual(target_stats["questions"][0]["rank"], 1)
        with get_connection(self.database_url) as connection:
            old_row = connection.execute(
                "SELECT enabled, replaced_by_question_id FROM questions WHERE id = ?",
                (question_id,),
            ).fetchone()
        self.assertFalse(bool(old_row["enabled"]))
        self.assertEqual(old_row["replaced_by_question_id"], replacement_id)

    def test_bundle_import_validates_and_commits_as_one_question(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        bundle_qml = "{A patient needs {} mg. The solution has {} mg/ml. How much is needed? []\n {500} {40} [12.5 ml]\n {600} {30} [20 ml]}"

        validate_payload = self.validate_import_payload(target["id"], qml_text=bundle_qml)
        self.assertTrue(validate_payload["ready_to_commit"])
        self.assertEqual(validate_payload["valid_row_count"], 1)
        self.assertEqual(validate_payload["rows"][0]["entry_kind"], "bundle")
        self.assertEqual(validate_payload["rows"][0]["start_line"], 1)
        self.assertEqual(validate_payload["rows"][0]["end_line"], 3)

        commit_payload = self.commit_import_payload(
            target["id"],
            [
                {
                    "start_line": 1,
                    "end_line": 3,
                    "entry_kind": "bundle",
                    "qml_text": bundle_qml,
                }
            ],
        )
        self.assertTrue(commit_payload["committed"])
        self.assertEqual(commit_payload["committed_count"], 1)

        with get_connection(self.database_url) as connection:
            row = connection.execute(
                """
                SELECT q.question_type, q.prompt, COUNT(bundles.id) AS variant_count
                FROM questions AS q
                LEFT JOIN question_bundles AS bundles ON bundles.question_id = q.id
                WHERE q.module_id = ?
                GROUP BY q.id, q.question_type, q.prompt
                """,
                (target["id"],),
            ).fetchone()
        self.assertEqual(row["question_type"], "bundle")
        self.assertIn("A patient needs {} mg.", row["prompt"])
        self.assertEqual(row["variant_count"], 2)

    def test_same_leaf_exact_noop_duplicate_has_no_side_effects(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])
        question_id = self.create_question_record(target["id"], "mot", [["against"]])["question_id"]

        user = self.create_user()
        session = self.start_quiz_session(user["id"], target["id"], 1)
        item = session["items"][0]
        self.submit_quiz_item(user["id"], session["id"], item["id"], ["against"])

        commit_payload = self.commit_import_payload(
            target["id"],
            [plain_import_entry(1, "mot [against]")],
        )
        self.assertFalse(commit_payload["committed"])
        self.assertEqual(commit_payload["exact_duplicate_count"], 1)
        self.assertEqual(commit_payload["committed_count"], 0)

        target_stats = self.get_stats_payload(user["id"], target["id"])
        self.assertEqual(len(target_stats["questions"]), 1)
        self.assertEqual(target_stats["questions"][0]["question_id"], question_id)
        self.assertEqual(target_stats["questions"][0]["attempts"], 1)
        self.assertEqual(target_stats["questions"][0]["accepted_answers"], [["against"]])

    def test_same_upload_changed_duplicate_blocks_commit_until_resolved(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        target = self.create_module_record("Target", norwegian["id"])

        validate_payload = self.validate_import_payload(
            target["id"],
            rows=[
                plain_import_entry(1, "selv [self]"),
                plain_import_entry(2, "selv [self | even]"),
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
                plain_import_entry(1, "selv [self]"),
                plain_import_entry(2, "selv [self | even]"),
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

        validate_payload = self.validate_import_payload(module_ids["target"], qml_text="hund [dog | canine | pooch]")
        self.assertEqual(validate_payload["review_rows"][0]["status"], "conflict")
        self.assertTrue(validate_payload["review_rows"][0]["blocking"])
        self.assertEqual(len(validate_payload["review_rows"][0]["matched_questions"]), 2)
        self.assertFalse(validate_payload["ready_to_commit"])

        commit_payload = self.commit_import_payload(
            module_ids["target"],
            [plain_import_entry(1, "hund [dog | canine | pooch]")],
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
