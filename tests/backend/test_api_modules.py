from test_support import PostgresBackendTestCase


class ModuleApiTests(PostgresBackendTestCase):
    def test_leaf_module_can_be_renamed_without_losing_question_access(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        nouns = self.create_module_record(
            "Nouns to English",
            norwegian["id"],
            "Translate the Norwegian term into English.",
        )
        self.create_question_record(
            nouns["id"],
            "hund",
            [["dog"]],
        )

        rename_response = self.client.patch(
            f"/api/modules/{nouns['id']}",
            json={
                "title": "Animals to English",
                "instruction": "Translate the animal term into English.",
            },
            headers=self.admin_headers,
        )
        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(rename_response.json()["full_slug"], "norwegian/animals_to_english")
        self.assertEqual(rename_response.json()["instruction"], "Translate the animal term into English.")

        tree_response = self.client.get("/api/modules/tree", headers=self.admin_headers)
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
                    "admin_verified": True,
                    "moderation_status": "verified",
                    "created_by_user_id": None,
                    "creator_display_name": None,
                    "children": [],
                }
            ],
        )

        user = self.create_user()
        stats_payload = self.get_stats_payload(user["id"], nouns["id"])
        self.assertEqual(stats_payload["questions"][0]["module_full_slug"], "norwegian/animals_to_english")
        self.assertEqual(stats_payload["questions"][0]["prompt"], "hund")

    def test_non_leaf_module_rename_is_rejected(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        self.create_module_record("Vocabulary", norwegian["id"])

        rename_response = self.client.patch(
            f"/api/modules/{norwegian['id']}",
            json={"title": "Language", "instruction": ""},
            headers=self.admin_headers,
        )
        self.assertEqual(rename_response.status_code, 400)
        self.assertEqual(rename_response.json()["detail"], "Only leaf modules can be renamed.")

    def test_question_delete_removes_question_without_reordering_remaining_siblings(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        weekdays = self.create_module_record("Weekdays", norwegian["id"])
        first_question_id = self.create_question_record(
            weekdays["id"],
            "mandag",
            [["Monday"]],
            rank=1,
        )["question_id"]
        second_question_id = self.create_question_record(
            weekdays["id"],
            "tirsdag",
            [["Tuesday"]],
            rank=2,
        )["question_id"]

        user = self.create_user()
        session = self.start_quiz_session(user["id"], weekdays["id"], 2)
        first_item = next(item for item in session["items"] if item["question_id"] == first_question_id)
        self.submit_quiz_item(user["id"], session["id"], first_item["id"], ["Monday"])
        self.set_review_flag(user["id"], first_question_id, True)

        delete_response = self.client.delete(f"/api/questions/{first_question_id}", headers=self.admin_headers)
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(
            delete_response.json(),
            {
                "question_id": first_question_id,
                "proposal_id": None,
                "admin_verified": True,
                "moderation_status": "verified",
                "delete_requested": False,
            },
        )

        stats_payload = self.get_stats_payload(user["id"], weekdays["id"])
        remaining_questions = stats_payload["questions"]
        self.assertEqual(len(remaining_questions), 1)
        self.assertEqual(remaining_questions[0]["question_id"], second_question_id)
        self.assertEqual(remaining_questions[0]["rank"], 2)

        missing_response = self.client.delete(f"/api/questions/{first_question_id}", headers=self.admin_headers)
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["detail"], f"Question {first_question_id} was not found.")
