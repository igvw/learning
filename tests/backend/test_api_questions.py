from test_support import PostgresBackendTestCase


class QuestionDetailApiTests(PostgresBackendTestCase):
    def test_question_detail_returns_editable_verified_question(self) -> None:
        geography = self.create_module_record("Question Detail Geography")
        capitals = self.create_module_record("Question Detail Capitals", geography["id"])
        question_id = self.create_question_record(
            capitals["id"],
            "What is the capital of Norway?",
            [["Oslo", "Christiania"]],
            rank=3,
        )["question_id"]
        user = self.create_user("alice-question-detail", "Alice Question Detail")
        self.set_review_flag(user["id"], question_id, True)

        response = self.client.get(
            f"/api/questions/{question_id}",
            headers=self.user_headers(user["id"]),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["question_id"], question_id)
        self.assertEqual(payload["module_id"], capitals["id"])
        self.assertEqual(payload["module_full_slug"], "question_detail_geography/question_detail_capitals")
        self.assertEqual(payload["prompt"], "What is the capital of Norway?")
        self.assertEqual(payload["question_type"], "single_text")
        self.assertEqual(payload["rank"], 1)
        self.assertEqual(payload["accepted_answers"], [["Oslo", "Christiania"]])
        self.assertTrue(payload["review_flag"])
        self.assertEqual(payload["segments"], [])
        self.assertIsNone(payload["bundle_qml"])
        self.assertIn("schedule", payload)

    def test_question_detail_returns_canonical_bundle_qml(self) -> None:
        pharmacy = self.create_module_record("Question Detail Pharmacy")
        calculations = self.create_module_record("Question Detail Calculations", pharmacy["id"])
        bundle_qml = (
            "{A patient needs {} mg. The solution has {} mg/ml. How much is needed? []\n"
            " {500} {40} [12.5 ml]\n"
            " {600} {30} [20 ml]}"
        )
        question_id = self.create_question_record(
            calculations["id"],
            "A patient needs {} mg. The solution has {} mg/ml. How much is needed? []",
            [],
            question_type="bundle",
            bundle_qml=bundle_qml,
        )["question_id"]
        user = self.create_user("alice-question-bundle-detail", "Alice Question Bundle Detail")

        response = self.client.get(
            f"/api/questions/{question_id}",
            headers=self.user_headers(user["id"]),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["question_type"], "bundle")
        self.assertEqual(payload["bundle_qml"], bundle_qml)
        self.assertEqual(payload["accepted_answers"], [])

    def test_question_detail_returns_404_for_missing_or_invisible_question(self) -> None:
        module = self.create_module_record("Question Detail Private")
        owner = self.create_user("alice-private-question", "Alice Private Question")
        viewer = self.create_user("bob-private-question", "Bob Private Question")
        create_response = self.client.post(
            "/api/questions",
            json={
                "module_id": module["id"],
                "prompt": "private prompt",
                "question_type": "single_text",
                "rank": 1,
                "accepted_answers": [["private"]],
                "segments": [],
            },
            headers=self.user_headers(owner["id"]),
        )
        self.assertEqual(create_response.status_code, 200)
        invisible_question_id = create_response.json()["question_id"]

        missing_response = self.client.get(
            "/api/questions/999999999",
            headers=self.user_headers(viewer["id"]),
        )
        invisible_response = self.client.get(
            f"/api/questions/{invisible_question_id}",
            headers=self.user_headers(viewer["id"]),
        )

        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(invisible_response.status_code, 404)
