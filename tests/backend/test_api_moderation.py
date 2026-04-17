from test_support import PostgresBackendTestCase


def _flatten_module_tree(nodes: list[dict]) -> list[dict]:
    flattened: list[dict] = []
    stack = list(nodes)
    while stack:
        node = stack.pop()
        flattened.append(node)
        stack.extend(node["children"])
    return flattened


class ModerationApiTests(PostgresBackendTestCase):
    def test_pending_module_is_visible_only_to_creator_and_admin_until_approved(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        alice = self.create_user(handle="alice", display_name="Alice")
        bob = self.create_user(handle="bob", display_name="Bob")

        create_response = self.client.post(
            "/api/modules",
            json={
                "title": "Vocabulary",
                "parent_id": norwegian["id"],
                "instruction": "Translate the Norwegian term into English.",
            },
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["admin_verified"], False)
        self.assertEqual(create_response.json()["moderation_status"], "pending")
        module_id = int(create_response.json()["id"])

        creator_tree = self.client.get("/api/modules/tree", headers=self.user_headers(int(alice["id"])))
        self.assertEqual(creator_tree.status_code, 200)
        self.assertIn(
            "norwegian/vocabulary",
            {node["full_slug"] for node in _flatten_module_tree(creator_tree.json())},
        )

        other_tree = self.client.get("/api/modules/tree", headers=self.user_headers(int(bob["id"])))
        self.assertEqual(other_tree.status_code, 200)
        self.assertNotIn(
            "norwegian/vocabulary",
            {node["full_slug"] for node in _flatten_module_tree(other_tree.json())},
        )

        admin_tree = self.client.get("/api/modules/tree", headers=self.admin_headers)
        self.assertEqual(admin_tree.status_code, 200)
        admin_module = next(node for node in _flatten_module_tree(admin_tree.json()) if node["id"] == module_id)
        self.assertEqual(admin_module["admin_verified"], False)

        approve_response = self.client.post(
            f"/api/moderation/modules/{module_id}",
            json={"action": "approve", "note": "Looks good."},
            headers=self.admin_headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["admin_verified"], True)
        self.assertEqual(approve_response.json()["moderation_status"], "verified")

        approved_tree = self.client.get("/api/modules/tree", headers=self.user_headers(int(bob["id"])))
        self.assertEqual(approved_tree.status_code, 200)
        self.assertIn(
            "norwegian/vocabulary",
            {node["full_slug"] for node in _flatten_module_tree(approved_tree.json())},
        )

    def test_pending_question_and_revision_overlay_are_scoped_until_admin_approval(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")
        bob = self.create_user(handle="bob", display_name="Bob")

        pending_question_response = self.client.post(
            "/api/questions",
            json={
                "module_id": words["id"],
                "prompt": "katt",
                "question_type": "single_text",
                "rank": 2,
                "accepted_answers": [["cat"]],
                "segments": [],
            },
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(pending_question_response.status_code, 200)
        pending_question_id = int(pending_question_response.json()["question_id"])
        self.assertEqual(pending_question_response.json()["admin_verified"], False)

        alice_stats_before = self.get_stats_payload(int(alice["id"]), words["id"])
        self.assertEqual(
            {question["prompt"] for question in alice_stats_before["questions"]},
            {"hund", "katt"},
        )
        bob_stats_before = self.get_stats_payload(int(bob["id"]), words["id"])
        self.assertEqual(
            {question["prompt"] for question in bob_stats_before["questions"]},
            {"hund"},
        )

        pending_question_queue = self.client.get("/api/moderation/queue", headers=self.admin_headers)
        self.assertEqual(pending_question_queue.status_code, 200)
        queued_question = next(
            question
            for question in pending_question_queue.json()["pending_questions"]
            if question["question_id"] == pending_question_id
        )
        self.assertEqual(queued_question["creator_display_name"], "Alice")

        approve_question_response = self.client.post(
            f"/api/moderation/questions/{pending_question_id}",
            json={"action": "approve", "note": "Publish it."},
            headers=self.admin_headers,
        )
        self.assertEqual(approve_question_response.status_code, 200)
        self.assertEqual(approve_question_response.json()["admin_verified"], True)

        bob_stats_after_question_approval = self.get_stats_payload(int(bob["id"]), words["id"])
        self.assertEqual(
            {question["prompt"] for question in bob_stats_after_question_approval["questions"]},
            {"hund", "katt"},
        )

        revise_response = self.client.post(
            f"/api/questions/{verified_question['question_id']}/revisions",
            json={
                "module_id": words["id"],
                "prompt": "hunden",
                "question_type": "single_text",
                "rank": 1,
                "accepted_answers": [["dog"]],
                "segments": [],
                "reset_stats": False,
            },
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(revise_response.status_code, 200)
        proposal_id = int(revise_response.json()["proposal_id"])

        alice_stats_with_proposal = self.get_stats_payload(int(alice["id"]), words["id"])
        alice_question = next(
            question
            for question in alice_stats_with_proposal["questions"]
            if question["question_id"] == verified_question["question_id"]
        )
        self.assertEqual(alice_question["prompt"], "hunden")
        self.assertEqual(alice_question["viewer_proposal"]["proposal_id"], proposal_id)

        bob_stats_with_original = self.get_stats_payload(int(bob["id"]), words["id"])
        bob_question = next(
            question
            for question in bob_stats_with_original["questions"]
            if question["question_id"] == verified_question["question_id"]
        )
        self.assertEqual(bob_question["prompt"], "hund")
        self.assertIsNone(bob_question["viewer_proposal"])

        approve_revision_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={"action": "approve", "note": "Use the revised wording."},
            headers=self.admin_headers,
        )
        self.assertEqual(approve_revision_response.status_code, 200)
        self.assertEqual(approve_revision_response.json()["status"], "approved")

        bob_stats_after_revision_approval = self.get_stats_payload(int(bob["id"]), words["id"])
        approved_question = next(
            question
            for question in bob_stats_after_revision_approval["questions"]
            if question["question_id"] == verified_question["question_id"]
        )
        self.assertEqual(approved_question["prompt"], "hunden")

    def test_delete_request_hides_question_only_for_proposer_until_admin_approval(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")
        bob = self.create_user(handle="bob", display_name="Bob")

        delete_response = self.client.delete(
            f"/api/questions/{verified_question['question_id']}",
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(delete_response.status_code, 200)
        proposal_id = int(delete_response.json()["proposal_id"])
        self.assertEqual(delete_response.json()["delete_requested"], True)

        alice_stats = self.get_stats_payload(int(alice["id"]), words["id"])
        self.assertEqual(alice_stats["questions"], [])

        bob_stats = self.get_stats_payload(int(bob["id"]), words["id"])
        self.assertEqual(len(bob_stats["questions"]), 1)
        self.assertEqual(bob_stats["questions"][0]["prompt"], "hund")

        alice_session = self.start_quiz_session(int(alice["id"]), words["id"], 5)
        self.assertEqual(alice_session["items"], [])

        bob_session = self.start_quiz_session(int(bob["id"]), words["id"], 5)
        self.assertEqual(len(bob_session["items"]), 1)
        self.assertEqual(bob_session["items"][0]["question_id"], verified_question["question_id"])

        queue_response = self.client.get("/api/moderation/queue", headers=self.admin_headers)
        self.assertEqual(queue_response.status_code, 200)
        queued_revision = next(
            proposal for proposal in queue_response.json()["pending_revisions"] if proposal["proposal_id"] == proposal_id
        )
        self.assertEqual(queued_revision["delete_requested"], True)

        approve_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={"action": "approve", "note": "Remove it."},
            headers=self.admin_headers,
        )
        self.assertEqual(approve_response.status_code, 200)

        bob_stats_after_approval = self.get_stats_payload(int(bob["id"]), words["id"])
        self.assertEqual(bob_stats_after_approval["questions"], [])
