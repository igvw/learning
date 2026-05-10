import unittest

import backend.app.services as services


class ServiceFacadeUnitTests(unittest.TestCase):
    def test_public_service_symbols_are_exposed_from_facade(self) -> None:
        expected_public_names = {
            "ServiceError",
            "NotFoundError",
            "ValidationError",
            "Actor",
            "actor_to_dict",
            "admin_exists",
            "bootstrap_admin",
            "bootstrap_admin_from_environment",
            "commit_question_import",
            "create_module",
            "create_question",
            "create_quiz_session",
            "create_user",
            "delete_module",
            "delete_rejected_module_submission",
            "delete_question",
            "export_verified_content_archive",
            "get_actor_from_token",
            "get_module_tree",
            "get_question",
            "get_stats",
            "list_moderation_queue",
            "list_my_contributions",
            "list_users",
            "login_user",
            "logout_session",
            "revise_question",
            "review_module_submission",
            "review_question_revision",
            "review_question_submission",
            "set_question_review_flag",
            "submit_answer",
            "sync_seed_content",
            "update_module",
            "update_user_password",
            "update_user_role",
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
