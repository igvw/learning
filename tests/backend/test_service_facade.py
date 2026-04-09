from __future__ import annotations

import unittest

import backend.app.services as services


class ServiceFacadeUnitTests(unittest.TestCase):
    def test_public_service_symbols_are_exposed_from_facade(self) -> None:
        expected_public_names = {
            "ServiceError",
            "NotFoundError",
            "ValidationError",
            "commit_question_import",
            "create_module",
            "create_question",
            "create_quiz_session",
            "create_user",
            "get_module_tree",
            "get_stats",
            "list_users",
            "revise_question",
            "set_question_review_flag",
            "submit_answer",
            "sync_seed_content",
            "validate_question_import",
        }

        self.assertEqual(set(services.__all__), expected_public_names)
        for name in expected_public_names:
            self.assertTrue(hasattr(services, name), name)

    def test_private_helpers_are_not_exposed_from_facade(self) -> None:
        unexpected_private_names = {
            "_bucketed_question_selection",
            "_existing_prompt_keys",
            "_validate_question_import_rows",
            "_unordered_multi_alignment",
        }

        for name in unexpected_private_names:
            self.assertFalse(hasattr(services, name), name)
