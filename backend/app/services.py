"""Public backend service facade.

App entrypoints should import public services from this module.
Private helpers belong in ``backend.app.service.*`` and should not be re-exported here.
"""

from .service.auth import (
    Actor,
    actor_to_dict,
    admin_exists,
    bootstrap_admin,
    bootstrap_admin_from_environment,
    get_actor_from_token,
    login_user,
    logout_session,
    update_user_password,
    update_user_role,
)
from .service.authoring import (
    create_question,
    delete_question,
    revise_question,
    set_question_review_flag,
    sync_seed_content,
)
from .service.catalog import (
    create_module,
    create_user,
    delete_module,
    export_verified_content_archive,
    get_module_tree,
    list_users,
    update_module,
)
from .service.errors import NotFoundError, ServiceError, ValidationError
from .service.imports import commit_question_import, validate_question_import
from .service.moderation import (
    delete_rejected_module_submission,
    list_moderation_queue,
    list_my_contributions,
    review_module_submission,
    review_question_revision,
    review_question_submission,
)
from .service.quiz import create_quiz_session, submit_answer
from .service.stats import get_stats


__all__ = [
    "ServiceError",
    "Actor",
    "NotFoundError",
    "ValidationError",
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
    "get_module_tree",
    "get_actor_from_token",
    "get_stats",
    "login_user",
    "list_moderation_queue",
    "list_my_contributions",
    "list_users",
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
]
