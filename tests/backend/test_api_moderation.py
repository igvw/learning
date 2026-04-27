from backend.app.database import get_connection
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
    def test_moderation_endpoints_reject_changes_requested_action(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")

        pending_module_response = self.client.post(
            "/api/modules",
            json={
                "title": "Vocabulary",
                "parent_id": norwegian["id"],
                "instruction": "Translate the Norwegian term into English.",
            },
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(pending_module_response.status_code, 200)
        pending_module_id = int(pending_module_response.json()["id"])

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

        revision_response = self.client.post(
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
        self.assertEqual(revision_response.status_code, 200)
        proposal_id = int(revision_response.json()["proposal_id"])

        module_reject_response = self.client.post(
            f"/api/moderation/modules/{pending_module_id}",
            json={"action": "changes_requested", "note": "Please revise."},
            headers=self.admin_headers,
        )
        self.assertEqual(module_reject_response.status_code, 422)

        question_reject_response = self.client.post(
            f"/api/moderation/questions/{pending_question_id}",
            json={"action": "changes_requested", "note": "Please revise."},
            headers=self.admin_headers,
        )
        self.assertEqual(question_reject_response.status_code, 422)

        revision_reject_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={"action": "changes_requested", "note": "Please revise."},
            headers=self.admin_headers,
        )
        self.assertEqual(revision_reject_response.status_code, 422)

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

    def test_rejected_modules_move_from_pending_queue_to_rejected_queue_and_leave_user_contributions(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        alice = self.create_user(handle="alice", display_name="Alice")

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
        module_id = int(create_response.json()["id"])

        queue_before = self.client.get("/api/moderation/queue", headers=self.admin_headers)
        self.assertEqual(queue_before.status_code, 200)
        self.assertIn(
            module_id,
            {module["id"] for module in queue_before.json()["pending_modules"]},
        )
        self.assertEqual(queue_before.json()["rejected_modules"], [])

        reject_response = self.client.post(
            f"/api/moderation/modules/{module_id}",
            json={"action": "reject", "note": "Not ready yet."},
            headers=self.admin_headers,
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["moderation_status"], "rejected")

        queue_after = self.client.get("/api/moderation/queue", headers=self.admin_headers)
        self.assertEqual(queue_after.status_code, 200)
        self.assertNotIn(
            module_id,
            {module["id"] for module in queue_after.json()["pending_modules"]},
        )
        self.assertIn(
            module_id,
            {module["id"] for module in queue_after.json()["rejected_modules"]},
        )

        contributions_response = self.client.get(
            "/api/contributions/me",
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(contributions_response.status_code, 200)
        self.assertNotIn(
            module_id,
            {module["id"] for module in contributions_response.json()["modules"]},
        )

    def test_admin_can_delete_rejected_leaf_module(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        alice = self.create_user(handle="alice", display_name="Alice")

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
        module_id = int(create_response.json()["id"])

        reject_response = self.client.post(
            f"/api/moderation/modules/{module_id}",
            json={"action": "reject", "note": "Not ready yet."},
            headers=self.admin_headers,
        )
        self.assertEqual(reject_response.status_code, 200)

        delete_response = self.client.delete(
            f"/api/moderation/modules/{module_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(delete_response.status_code, 204)

        with get_connection(self.database_url) as connection:
            deleted_module = connection.execute(
                "SELECT id FROM modules WHERE id = ?",
                (module_id,),
            ).fetchone()
        self.assertIsNone(deleted_module)

    def test_admin_can_delete_rejected_module_subtree_and_cascade_descendant_questions(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        rejected_root = self.create_module_record("Rejected Root", norwegian["id"])
        pending_child = self.create_module_record("Pending Child", rejected_root["id"])
        rejected_leaf = self.create_module_record("Rejected Leaf", pending_child["id"])
        question = self.create_question_record(rejected_leaf["id"], "hund", [["dog"]], rank=1)

        with get_connection(self.database_url) as connection:
            connection.execute(
                "UPDATE modules SET admin_verified = 0, moderation_status = 'rejected' WHERE id = ?",
                (rejected_root["id"],),
            )
            connection.execute(
                "UPDATE modules SET admin_verified = 0, moderation_status = 'pending' WHERE id = ?",
                (pending_child["id"],),
            )
            connection.execute(
                "UPDATE modules SET admin_verified = 0, moderation_status = 'rejected' WHERE id = ?",
                (rejected_leaf["id"],),
            )

        delete_response = self.client.delete(
            f"/api/moderation/modules/{rejected_root['id']}",
            headers=self.admin_headers,
        )
        self.assertEqual(delete_response.status_code, 204)

        with get_connection(self.database_url) as connection:
            remaining_modules = connection.execute(
                "SELECT id FROM modules WHERE id IN (?, ?, ?)",
                (rejected_root["id"], pending_child["id"], rejected_leaf["id"]),
            ).fetchall()
            remaining_question = connection.execute(
                "SELECT id FROM questions WHERE id = ?",
                (question["question_id"],),
            ).fetchone()
        self.assertEqual(remaining_modules, [])
        self.assertIsNone(remaining_question)

    def test_rejected_module_delete_refuses_verified_descendants(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        rejected_root = self.create_module_record("Rejected Root", norwegian["id"])
        verified_child = self.create_module_record("Verified Child", rejected_root["id"])

        with get_connection(self.database_url) as connection:
            connection.execute(
                "UPDATE modules SET admin_verified = 0, moderation_status = 'rejected' WHERE id = ?",
                (rejected_root["id"],),
            )
            connection.execute(
                "UPDATE modules SET admin_verified = 1, moderation_status = 'verified' WHERE id = ?",
                (verified_child["id"],),
            )

        delete_response = self.client.delete(
            f"/api/moderation/modules/{rejected_root['id']}",
            headers=self.admin_headers,
        )
        self.assertEqual(delete_response.status_code, 400)
        self.assertEqual(
            delete_response.json()["detail"],
            "Cannot delete a rejected module subtree that contains verified descendants.",
        )

    def test_rejected_module_delete_refuses_pending_or_verified_targets(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        pending_module = self.create_module_record("Pending Module", norwegian["id"])
        verified_module = self.create_module_record("Verified Module", norwegian["id"])

        with get_connection(self.database_url) as connection:
            connection.execute(
                "UPDATE modules SET admin_verified = 0, moderation_status = 'pending' WHERE id = ?",
                (pending_module["id"],),
            )

        pending_delete = self.client.delete(
            f"/api/moderation/modules/{pending_module['id']}",
            headers=self.admin_headers,
        )
        self.assertEqual(pending_delete.status_code, 400)
        self.assertEqual(
            pending_delete.json()["detail"],
            "Only rejected unverified modules can be deleted from moderation.",
        )

        verified_delete = self.client.delete(
            f"/api/moderation/modules/{verified_module['id']}",
            headers=self.admin_headers,
        )
        self.assertEqual(verified_delete.status_code, 400)
        self.assertEqual(
            verified_delete.json()["detail"],
            "Only rejected unverified modules can be deleted from moderation.",
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
        self.assertNotIn(
            verified_question["question_id"],
            {question["question_id"] for question in alice_stats_with_proposal["questions"]},
        )

        alice_session = self.start_quiz_session(int(alice["id"]), words["id"], 5)
        self.assertNotIn(
            verified_question["question_id"],
            {item["question_id"] for item in alice_session["items"]},
        )

        bob_stats_with_original = self.get_stats_payload(int(bob["id"]), words["id"])
        bob_question = next(
            question
            for question in bob_stats_with_original["questions"]
            if question["question_id"] == verified_question["question_id"]
        )
        self.assertEqual(bob_question["prompt"], "hund")

        bob_session = self.start_quiz_session(int(bob["id"]), words["id"], 5)
        self.assertIn(
            verified_question["question_id"],
            {item["question_id"] for item in bob_session["items"]},
        )

        contributions_response = self.client.get(
            "/api/contributions/me",
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(contributions_response.status_code, 200)
        proposed_revision = next(
            proposal
            for proposal in contributions_response.json()["revisions"]
            if proposal["proposal_id"] == proposal_id
        )
        self.assertEqual(proposed_revision["proposed_prompt"], "hunden")

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
            if question["prompt"] == "hunden"
        )
        self.assertNotEqual(approved_question["question_id"], verified_question["question_id"])
        self.assertEqual(
            {question["prompt"] for question in bob_stats_after_revision_approval["questions"]},
            {"hunden", "katt"},
        )

    def test_admin_can_approve_revision_with_edited_override(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")

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

        approve_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={
                "action": "approve",
                "note": "Tighten the wording.",
                "edited_revision": {
                    "module_id": words["id"],
                    "prompt": "hunden min",
                    "question_type": "single_text",
                    "rank": 1,
                    "accepted_answers": [["my dog"]],
                    "segments": [],
                    "reset_stats": True,
                },
            },
            headers=self.admin_headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")

        stats_after = self.get_stats_payload(int(alice["id"]), words["id"])
        self.assertEqual(len(stats_after["questions"]), 1)
        revised_question = stats_after["questions"][0]
        self.assertNotEqual(revised_question["question_id"], verified_question["question_id"])
        self.assertEqual(revised_question["prompt"], "hunden min")
        self.assertEqual(revised_question["accepted_answers"], [["my dog"]])

    def test_admin_can_approve_revision_and_reset_stats_for_all_users(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")
        bob = self.create_user(handle="bob", display_name="Bob")

        alice_session = self.start_quiz_session(int(alice["id"]), words["id"], 1)
        self.submit_quiz_item(int(alice["id"]), alice_session["id"], alice_session["items"][0]["id"], ["dog"])
        bob_session = self.start_quiz_session(int(bob["id"]), words["id"], 1)
        self.submit_quiz_item(int(bob["id"]), bob_session["id"], bob_session["items"][0]["id"], ["dog"])

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

        approve_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={
                "action": "approve",
                "note": "Approve and reset.",
                "reset_stats": True,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")

        alice_stats = self.get_stats_payload(int(alice["id"]), words["id"])
        self.assertEqual(len(alice_stats["questions"]), 1)
        alice_question = alice_stats["questions"][0]
        self.assertNotEqual(alice_question["question_id"], verified_question["question_id"])
        self.assertEqual(alice_question["prompt"], "hunden")
        self.assertEqual(alice_question["attempts"], 0)
        self.assertEqual(alice_question["schedule"]["logical_bucket"], "unseen")

        bob_stats = self.get_stats_payload(int(bob["id"]), words["id"])
        self.assertEqual(len(bob_stats["questions"]), 1)
        bob_question = bob_stats["questions"][0]
        self.assertEqual(bob_question["question_id"], alice_question["question_id"])
        self.assertEqual(bob_question["prompt"], "hunden")
        self.assertEqual(bob_question["attempts"], 0)
        self.assertEqual(bob_question["schedule"]["logical_bucket"], "unseen")

    def test_delete_request_can_be_approved_as_an_edited_revision(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")

        delete_response = self.client.delete(
            f"/api/questions/{verified_question['question_id']}",
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(delete_response.status_code, 200)
        proposal_id = int(delete_response.json()["proposal_id"])

        approve_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={
                "action": "approve",
                "note": "Keep it, but revise it.",
                "edited_revision": {
                    "module_id": words["id"],
                    "prompt": "hunden",
                    "question_type": "single_text",
                    "rank": 1,
                    "accepted_answers": [["the dog"]],
                    "segments": [],
                    "reset_stats": False,
                },
            },
            headers=self.admin_headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")

        stats_after = self.get_stats_payload(int(alice["id"]), words["id"])
        self.assertEqual(len(stats_after["questions"]), 1)
        self.assertEqual(stats_after["questions"][0]["prompt"], "hunden")
        self.assertEqual(stats_after["questions"][0]["accepted_answers"], [["the dog"]])

    def test_reject_rejects_edited_revision_payload(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")

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

        reject_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={
                "action": "reject",
                "note": "No thanks.",
                "edited_revision": {
                    "module_id": words["id"],
                    "prompt": "hunden min",
                    "question_type": "single_text",
                    "rank": 1,
                    "accepted_answers": [["my dog"]],
                    "segments": [],
                    "reset_stats": False,
                },
            },
            headers=self.admin_headers,
        )
        self.assertEqual(reject_response.status_code, 400)
        self.assertEqual(
            reject_response.json()["detail"],
            "Edited revisions can only be submitted when approving a proposal.",
        )

    def test_reject_rejects_reset_stats_payload(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")

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

        reject_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={"action": "reject", "note": "No thanks.", "reset_stats": True},
            headers=self.admin_headers,
        )
        self.assertEqual(reject_response.status_code, 400)
        self.assertEqual(
            reject_response.json()["detail"],
            "Reset stats can only be submitted when approving a proposal.",
        )

    def test_rejected_revision_returns_question_to_study_flow_and_hides_proposal_from_user_ui(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")

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

        reject_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={"action": "reject", "note": "No thanks."},
            headers=self.admin_headers,
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], "rejected")

        queue_response = self.client.get("/api/moderation/queue", headers=self.admin_headers)
        self.assertEqual(queue_response.status_code, 200)
        self.assertNotIn(
            proposal_id,
            {proposal["proposal_id"] for proposal in queue_response.json()["pending_revisions"]},
        )

        contributions_response = self.client.get(
            "/api/contributions/me",
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(contributions_response.status_code, 200)
        self.assertNotIn(
            proposal_id,
            {proposal["proposal_id"] for proposal in contributions_response.json()["revisions"]},
        )

        stats_after_rejection = self.get_stats_payload(int(alice["id"]), words["id"])
        restored_question = next(
            question
            for question in stats_after_rejection["questions"]
            if question["question_id"] == verified_question["question_id"]
        )
        self.assertEqual(restored_question["prompt"], "hund")

        session_after_rejection = self.start_quiz_session(int(alice["id"]), words["id"], 5)
        self.assertIn(
            verified_question["question_id"],
            {item["question_id"] for item in session_after_rejection["items"]},
        )

        with get_connection(self.database_url) as connection:
            stored_rejection = connection.execute(
                """
                SELECT status, admin_review_note
                FROM question_revision_proposals
                WHERE id = ?
                """,
                (proposal_id,),
            ).fetchone()
        self.assertIsNotNone(stored_rejection)
        self.assertEqual(stored_rejection["status"], "rejected")
        self.assertEqual(stored_rejection["admin_review_note"], "No thanks.")

    def test_reopened_pending_revision_with_stale_review_metadata_is_visible(self) -> None:
        norwegian = self.create_module_record("Norwegian")
        words = self.create_module_record("Words", norwegian["id"])
        verified_question = self.create_question_record(words["id"], "hund", [["dog"]], rank=1)
        alice = self.create_user(handle="alice", display_name="Alice")

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

        reject_response = self.client.post(
            f"/api/moderation/question-revisions/{proposal_id}",
            json={"action": "reject", "note": "No thanks."},
            headers=self.admin_headers,
        )
        self.assertEqual(reject_response.status_code, 200)

        with get_connection(self.database_url) as connection:
            connection.execute(
                """
                UPDATE question_revision_proposals
                SET status = 'pending'
                WHERE id = ?
                """,
                (proposal_id,),
            )

        queue_response = self.client.get("/api/moderation/queue", headers=self.admin_headers)
        self.assertEqual(queue_response.status_code, 200)
        reopened_revision = next(
            proposal
            for proposal in queue_response.json()["pending_revisions"]
            if proposal["proposal_id"] == proposal_id
        )
        self.assertEqual(reopened_revision["status"], "pending")

        contributions_response = self.client.get(
            "/api/contributions/me",
            headers=self.user_headers(int(alice["id"])),
        )
        self.assertEqual(contributions_response.status_code, 200)
        reopened_contribution = next(
            proposal
            for proposal in contributions_response.json()["revisions"]
            if proposal["proposal_id"] == proposal_id
        )
        self.assertEqual(reopened_contribution["status"], "pending")
        self.assertEqual(reopened_contribution["admin_review_note"], "No thanks.")

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
