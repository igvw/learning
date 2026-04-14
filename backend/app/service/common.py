import json
import random
import re
from datetime import datetime, timedelta
from typing import Any

from ..config import FULL_CREDIT_TOLERANCE
from ..qml import render_prompt_and_answers
from ..schemas import QuestionDraftIn


class ServiceError(Exception):
    status_code = 400


class NotFoundError(ServiceError):
    status_code = 404


class ValidationError(ServiceError):
    status_code = 400


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")
    return slug or "module"


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def title_from_slug(slug: str) -> str:
    words = [word for word in slug.replace("_", " ").strip().split() if word]
    return " ".join(word[:1].upper() + word[1:] for word in words)


def parse_iso_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def add_interval_to_timestamp(value: str, interval: timedelta) -> str:
    return (parse_iso_timestamp(value) + interval).isoformat()


def is_full_credit(score_earned: float | None, score_possible: float | None) -> bool:
    if score_earned is None or score_possible is None or score_possible <= 0:
        return False
    return score_earned >= (score_possible - FULL_CREDIT_TOLERANCE)


def json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def escape_qml_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("{", "\\{").replace("}", "\\}").replace("|", "\\|").replace(",", "\\,")


def render_inline_segments(segments: list[str]) -> str:
    return "[_]".join(segments)


def serialize_type_config(payload: QuestionDraftIn) -> dict[str, Any]:
    return {
        "accepted_answers": payload.accepted_answers,
        "segments": payload.segments,
    }


def public_type_config(question_type: str, type_config: dict[str, Any]) -> dict[str, Any]:
    if question_type in {"single_text", "computed_text"}:
        return {"expected_slots": 1}
    if question_type in {"multi_text", "ordered_multi"}:
        return {"expected_slots": len(type_config.get("accepted_answers", []))}
    return {"segments": type_config.get("segments", [])}


def canonical_answers(type_config: dict[str, Any]) -> list[str]:
    return [" / ".join(group) for group in type_config.get("accepted_answers", [])]


def default_answers(type_config: dict[str, Any]) -> list[str]:
    return [group[0] if group else "" for group in type_config.get("accepted_answers", [])]


def accepted_answer_groups(type_config: dict[str, Any]) -> list[list[str]]:
    return [list(group) for group in type_config.get("accepted_answers", [])]


def answer_blocks(type_config: dict[str, Any]) -> list[str]:
    return [" | ".join(group) for group in type_config.get("accepted_answers", [])]


def score_possible(type_config: dict[str, Any]) -> float:
    return 1.0


def preview_prompt(prompt: str, question_type: str, type_config: dict[str, Any]) -> str:
    if question_type == "inline_cloze":
        rendered = render_inline_segments(type_config.get("segments", []))
        return rendered if len(rendered) <= 120 else f"{rendered[:117]}..."
    return prompt if len(prompt) <= 120 else f"{prompt[:117]}..."


def question_prompt_key(question_type: str, prompt: str, type_config: dict[str, Any]) -> str:
    if question_type == "inline_cloze":
        return normalize_text(render_inline_segments(type_config.get("segments", [])))
    return normalize_text(prompt)


def question_identity_key(question_type: str, prompt: str, type_config: dict[str, Any]) -> tuple[str, str]:
    return question_type, question_prompt_key(question_type, prompt, type_config)


def build_qml_line(question_type: str, prompt: str, type_config: dict[str, Any]) -> str:
    accepted_answers = type_config.get("accepted_answers", [])
    if question_type in {"single_text", "computed_text"}:
        content = " | ".join(escape_qml_text(value) for value in accepted_answers[0])
        return f"{escape_qml_text(prompt.strip())} [{content}]"
    if question_type == "multi_text":
        content = ", ".join(" | ".join(escape_qml_text(value) for value in group) for group in accepted_answers)
        return f"{escape_qml_text(prompt.strip())} {{{content}}}"
    if question_type == "ordered_multi":
        content = ", ".join(" | ".join(escape_qml_text(value) for value in group) for group in accepted_answers)
        return f"{escape_qml_text(prompt.strip())} [{content}]"

    segments = type_config.get("segments", [])
    line_parts: list[str] = []
    for index, group in enumerate(accepted_answers):
        line_parts.append(escape_qml_text(segments[index] if index < len(segments) else ""))
        line_parts.append(f"[{' | '.join(escape_qml_text(value) for value in group)}]")
    if len(segments) > len(accepted_answers):
        line_parts.append(escape_qml_text(segments[-1]))
    return "".join(line_parts)


def resolved_runtime(
    question_type: str,
    prompt: str,
    type_config: dict[str, Any],
    *,
    rng: random.Random | None = None,
) -> tuple[str, dict[str, Any]]:
    if question_type != "computed_text":
        return prompt, type_config

    rendered_prompt, rendered_answers = render_prompt_and_answers(
        prompt=prompt,
        accepted_answers=type_config.get("accepted_answers", []),
        rng=rng,
    )
    return rendered_prompt, {"accepted_answers": rendered_answers, "segments": []}
