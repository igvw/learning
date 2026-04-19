import copy
import itertools
from typing import Any

from ..settings import schedule_timezone_name
from .questions import accepted_answer_groups, canonical_answers, default_answers, public_type_config
from .quiz import evaluate_answers


_DEMO_ROOT_ID = 9000
_DEMO_LEAF_ID = 9001
_DEMO_MODULE_TREE = [
    {
        "id": _DEMO_ROOT_ID,
        "title": "Demo",
        "slug": "demo",
        "full_slug": "demo",
        "instruction": "Short showcase deck for trying the app without saving changes.",
        "admin_verified": True,
        "moderation_status": "verified",
        "created_by_user_id": None,
        "creator_display_name": None,
        "children": [
            {
                "id": _DEMO_LEAF_ID,
                "title": "Basics",
                "slug": "basics",
                "full_slug": "demo/basics",
                "instruction": "Translate or fill in the most common beginner items.",
                "admin_verified": True,
                "moderation_status": "verified",
                "created_by_user_id": None,
                "creator_display_name": None,
                "children": [],
            }
        ],
    }
]
_DEMO_QUESTIONS = [
    {
        "question_id": 9101,
        "module_id": _DEMO_LEAF_ID,
        "module_instruction": "Translate or fill in the most common beginner items.",
        "module_full_slug": "demo/basics",
        "prompt": "house",
        "question_type": "single_text",
        "rank": 1,
        "type_config": {"accepted_answers": [["hus"]], "segments": []},
        "attempts": 8,
        "correct_percentage": 0.75,
        "schedule": {
            "bucket": "cooling",
            "logical_bucket": "1d",
            "recovery_streak": None,
            "interval_step": 4,
            "last_incorrect_at": None,
            "next_due_at": "2030-01-01T00:00:00+00:00",
        },
    },
    {
        "question_id": 9102,
        "module_id": _DEMO_LEAF_ID,
        "module_instruction": "Translate or fill in the most common beginner items.",
        "module_full_slug": "demo/basics",
        "prompt": "dog",
        "question_type": "single_text",
        "rank": 2,
        "type_config": {"accepted_answers": [["hund"], ["bikkje"]], "segments": []},
        "attempts": 6,
        "correct_percentage": 0.5,
        "schedule": {
            "bucket": "due_review",
            "logical_bucket": "review",
            "recovery_streak": None,
            "interval_step": 1,
            "last_incorrect_at": "2030-01-01T07:00:00+00:00",
            "next_due_at": "2030-01-01T08:00:00+00:00",
        },
    },
    {
        "question_id": 9103,
        "module_id": _DEMO_LEAF_ID,
        "module_instruction": "Translate or fill in the most common beginner items.",
        "module_full_slug": "demo/basics",
        "prompt": "The sky is [_].",
        "question_type": "inline_cloze",
        "rank": 3,
        "type_config": {"accepted_answers": [["blue"]], "segments": ["The sky is ", "."]},
        "attempts": 5,
        "correct_percentage": 0.8,
        "schedule": {
            "bucket": "cooling",
            "logical_bucket": "7d",
            "recovery_streak": None,
            "interval_step": 6,
            "last_incorrect_at": None,
            "next_due_at": "2030-01-07T00:00:00+00:00",
        },
    },
    {
        "question_id": 9104,
        "module_id": _DEMO_LEAF_ID,
        "module_instruction": "Translate or fill in the most common beginner items.",
        "module_full_slug": "demo/basics",
        "prompt": "Name the colors",
        "question_type": "multi_text",
        "rank": 4,
        "type_config": {"accepted_answers": [["red"], ["blue"]], "segments": []},
        "attempts": 4,
        "correct_percentage": 0.5,
        "schedule": {
            "bucket": "cooling",
            "logical_bucket": "30d",
            "recovery_streak": None,
            "interval_step": 8,
            "last_incorrect_at": None,
            "next_due_at": "2030-02-01T00:00:00+00:00",
        },
    },
]
_DEMO_RECENT_SESSIONS = [
    {
        "session_id": 8801,
        "created_at": "2030-01-01T08:00:00+00:00",
        "answered_count": 4,
        "correct_count": 3,
        "score_possible": 4,
        "accuracy": 0.75,
    },
    {
        "session_id": 8802,
        "created_at": "2030-01-02T08:00:00+00:00",
        "answered_count": 4,
        "correct_count": 2,
        "score_possible": 4,
        "accuracy": 0.5,
    },
]
_DEMO_QUIZ_SESSION_COUNTER = itertools.count(9901)
_DEMO_QUIZ_SESSIONS: dict[int, dict[str, Any]] = {}
_DEMO_REVIEW_FLAGS: dict[str, dict[int, bool]] = {}


def demo_module_tree() -> list[dict[str, Any]]:
    return copy.deepcopy(_DEMO_MODULE_TREE)


def _demo_questions_for_scope(module_id: int | None) -> list[dict[str, Any]]:
    if module_id is None or module_id in {_DEMO_ROOT_ID, _DEMO_LEAF_ID}:
        return [copy.deepcopy(question) for question in _DEMO_QUESTIONS]
    return []


def create_demo_quiz_session(*, module_id: int | None, count: int) -> dict[str, Any]:
    questions = _demo_questions_for_scope(module_id)[:count]
    session_id = next(_DEMO_QUIZ_SESSION_COUNTER)
    items: list[dict[str, Any]] = []
    for index, question in enumerate(questions, start=1):
        items.append(
            {
                "id": question["question_id"],
                "position": index,
                "question_id": question["question_id"],
                "module_id": question["module_id"],
                "module_instruction": question["module_instruction"],
                "review_flag": False,
                "prompt": question["prompt"],
                "question_type": question["question_type"],
                "rank": question["rank"],
                "type_config": public_type_config(question["question_type"], question["type_config"]),
                "admin_verified": True,
                "moderation_status": "verified",
                "created_by_user_id": None,
                "creator_display_name": None,
                "viewer_proposal": None,
                "submitted_answer": None,
                "is_correct": None,
                "score_earned": None,
                "score_possible": 1.0,
            }
        )
    _DEMO_QUIZ_SESSIONS[session_id] = {"module_id": module_id, "items": items, "questions": questions}
    return {"id": session_id, "module_id": module_id, "completed_at": None, "items": items}


def submit_demo_answer(*, session_id: int, item_id: int, answers: list[str]) -> dict[str, Any]:
    session = _DEMO_QUIZ_SESSIONS.get(session_id)
    if session is None:
        raise ValueError("Demo quiz session was not found.")
    item = next((candidate for candidate in session["items"] if candidate["question_id"] == item_id), None)
    question = next((candidate for candidate in session["questions"] if candidate["question_id"] == item_id), None)
    if item is None or question is None:
        raise ValueError("Demo quiz item was not found.")
    if item["score_earned"] is not None:
        raise ValueError("Demo quiz item has already been answered.")

    is_correct, score_earned, score_possible, slot_results, matched_default_answers = evaluate_answers(
        question["question_type"],
        question["type_config"],
        answers,
    )
    item.update(
        {
            "submitted_answer": list(answers),
            "is_correct": is_correct,
            "score_earned": score_earned,
            "score_possible": score_possible,
        }
    )
    session_completed = all(candidate["score_earned"] is not None for candidate in session["items"])
    return {
        "item_id": item_id,
        "is_correct": is_correct,
        "score_earned": score_earned,
        "score_possible": score_possible,
        "slot_results": slot_results,
        "canonical_answers": canonical_answers(question["type_config"]),
        "default_answers": default_answers(question["type_config"]),
        "accepted_answer_groups": accepted_answer_groups(question["type_config"]),
        "matched_default_answers": matched_default_answers,
        "session_completed": session_completed,
        "submitted_answer": answers,
    }


def set_demo_review_flag(*, actor_key: str, question_id: int, review_flag: bool) -> dict[str, Any]:
    flags = _DEMO_REVIEW_FLAGS.setdefault(actor_key, {})
    flags[question_id] = review_flag
    return {"question_id": question_id, "review_flag": review_flag}


def get_demo_stats(*, actor_key: str, module_id: int | None, review_only: bool) -> dict[str, Any]:
    review_flags = _DEMO_REVIEW_FLAGS.setdefault(actor_key, {})
    questions: list[dict[str, Any]] = []
    for question in _demo_questions_for_scope(module_id):
        review_flag = review_flags.get(question["question_id"], False)
        if review_only and not review_flag:
            continue
        questions.append(
            {
                "question_id": question["question_id"],
                "module_id": question["module_id"],
                "module_full_slug": question["module_full_slug"],
                "prompt": question["prompt"],
                "prompt_preview": question["prompt"],
                "question_type": question["question_type"],
                "rank": question["rank"],
                "attempts": question["attempts"],
                "correct_percentage": question["correct_percentage"],
                "first_asked_at": "2030-01-01T08:00:00+00:00",
                "last_asked_at": "2030-01-02T08:00:00+00:00",
                "review_flag": review_flag,
                "admin_verified": True,
                "moderation_status": "verified",
                "created_by_user_id": None,
                "creator_display_name": None,
                "viewer_proposal": None,
                "accepted_answers": question["type_config"]["accepted_answers"],
                "segments": question["type_config"].get("segments", []),
                "recent_incorrect_answers": [],
                "schedule": question["schedule"],
            }
        )
    total_questions = len(_demo_questions_for_scope(module_id))
    reviewed_questions = sum(1 for question in _demo_questions_for_scope(module_id) if review_flags.get(question["question_id"], False))
    return {
        "summary": {
            "total_questions": total_questions,
            "reviewed_questions": reviewed_questions,
            "total_attempts": sum(question["attempts"] for question in _demo_questions_for_scope(module_id)),
            "total_correct": 11.0,
            "total_possible": 17.0,
            "accuracy": 11.0 / 17.0,
        },
        "schedule_timezone": schedule_timezone_name(),
        "recent_sessions": copy.deepcopy(_DEMO_RECENT_SESSIONS),
        "questions": questions,
    }
