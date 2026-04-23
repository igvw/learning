import random
from typing import Any

from ..schemas import QuestionDraftIn
from .bundles import bundle_summary, normalize_bundle_payload
from .text import normalize_text


def _escape_qml_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("|", "\\|")
        .replace(",", "\\,")
    )


def _render_inline_segments(segments: list[str]) -> str:
    return "[_]".join(segments)


def serialize_type_config(payload: QuestionDraftIn) -> dict[str, Any]:
    if payload.question_type == "bundle":
        prompt, variants, _ = normalize_bundle_payload(payload)
        return bundle_summary(prompt, variants)
    return {
        "accepted_answers": payload.accepted_answers,
        "segments": payload.segments,
    }


def public_type_config(question_type: str, type_config: dict[str, Any]) -> dict[str, Any]:
    if question_type in {"single_text", "bundle"}:
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
    _ = type_config
    return 1.0


def preview_prompt(prompt: str, question_type: str, type_config: dict[str, Any]) -> str:
    if question_type == "inline_cloze":
        rendered = _render_inline_segments(type_config.get("segments", []))
        return rendered if len(rendered) <= 120 else f"{rendered[:117]}..."
    return prompt if len(prompt) <= 120 else f"{prompt[:117]}..."


def question_prompt_key(question_type: str, prompt: str, type_config: dict[str, Any]) -> str:
    _ = type_config
    if question_type == "inline_cloze":
        return normalize_text(_render_inline_segments(type_config.get("segments", [])))
    return normalize_text(prompt)


def stored_prompt_key(question_type: str, prompt: str, type_config: dict[str, Any]) -> str:
    return question_prompt_key(question_type, prompt, type_config)


def stored_prompt_key_for_payload(payload: QuestionDraftIn) -> str:
    type_config = serialize_type_config(payload)
    return stored_prompt_key(payload.question_type, payload.prompt, type_config)


def question_identity_key(question_type: str, prompt: str, type_config: dict[str, Any]) -> tuple[str, str]:
    return question_type, question_prompt_key(question_type, prompt, type_config)


def build_qml_line(question_type: str, prompt: str, type_config: dict[str, Any]) -> str:
    if question_type == "bundle":
        raise ValueError("Bundle questions require canonical bundle QML, not build_qml_line().")

    accepted_answers = type_config.get("accepted_answers", [])
    if question_type == "single_text":
        content = " | ".join(_escape_qml_text(value) for value in accepted_answers[0])
        return f"{_escape_qml_text(prompt.strip())} [{content}]"
    if question_type == "multi_text":
        content = ", ".join(" | ".join(_escape_qml_text(value) for value in group) for group in accepted_answers)
        return f"{_escape_qml_text(prompt.strip())} {{{content}}}"
    if question_type == "ordered_multi":
        content = ", ".join(" | ".join(_escape_qml_text(value) for value in group) for group in accepted_answers)
        return f"{_escape_qml_text(prompt.strip())} [{content}]"

    segments = type_config.get("segments", [])
    line_parts: list[str] = []
    for index, group in enumerate(accepted_answers):
        line_parts.append(_escape_qml_text(segments[index] if index < len(segments) else ""))
        line_parts.append(f"[{' | '.join(_escape_qml_text(value) for value in group)}]")
    if len(segments) > len(accepted_answers):
        line_parts.append(_escape_qml_text(segments[-1]))
    return "".join(line_parts)


def resolved_runtime(
    question_type: str,
    prompt: str,
    type_config: dict[str, Any],
    *,
    rng: random.Random | None = None,
) -> tuple[str, dict[str, Any]]:
    _ = rng
    return prompt, type_config
