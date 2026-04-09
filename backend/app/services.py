"""Public backend service facade.

App entrypoints should import public services from this module.
Private helpers belong in ``backend.app.service.*`` and should not be re-exported here.
"""

from .service.authoring import (
    create_question,
    revise_question,
    set_question_review_flag,
    sync_seed_content,
)
from .service.catalog import create_module, create_user, get_module_tree, list_users
from .service.common import NotFoundError, ServiceError, ValidationError
from .service.imports import commit_question_import, validate_question_import
from .service.quiz import create_quiz_session, submit_answer
from .service.stats import get_stats


__all__ = [
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
]
