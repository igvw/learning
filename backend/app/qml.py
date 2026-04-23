import json
from typing import Any


class QMLError(ValueError):
    pass


def split_escaped(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escape = False
    for char in text:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == separator:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if escape:
        raise QMLError("Dangling escape sequence.")
    parts.append("".join(current))
    return parts


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


def _split_answer_group(text: str) -> list[str]:
    answers = [value.strip() for value in split_escaped(text, "|") if value.strip()]
    if not answers:
        raise QMLError("Each answer slot needs at least one accepted answer.")
    return answers


def _find_trailing_box(line: str) -> tuple[int, int, str, str] | None:
    stripped = line.rstrip()
    if not stripped:
        return None
    closing = stripped[-1]
    if closing not in {"]", "}"}:
        return None
    opening = "[" if closing == "]" else "{"
    depth = 0
    escape = False
    start_index: int | None = None
    for index, char in enumerate(stripped):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == opening:
            if depth == 0:
                start_index = index
            depth += 1
        elif char == closing:
            depth -= 1
            if depth < 0:
                raise QMLError("Malformed answer box.")
            if depth == 0 and index == len(stripped) - 1 and start_index is not None:
                return start_index, index, opening, stripped[start_index + 1 : index]
    return None


def _parse_inline_collapse_groups(line: str) -> tuple[str, list[list[str]], list[str]]:
    segments: list[str] = []
    accepted_answers: list[list[str]] = []
    current_segment: list[str] = []
    current_group: list[str] | None = None
    escape = False
    saw_group = False

    for char in line:
        if escape:
            target = current_group if current_group is not None else current_segment
            target.append(char)
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if current_group is None:
            if char == "[":
                saw_group = True
                segments.append("".join(current_segment))
                current_segment = []
                current_group = []
                continue
            if char == "]":
                raise QMLError("Malformed inline cloze question.")
            current_segment.append(char)
            continue
        if char == "]":
            accepted_answers.append(_split_answer_group("".join(current_group)))
            current_group = None
            continue
        current_group.append(char)

    if escape or current_group is not None or not saw_group:
        raise QMLError("Malformed inline cloze question.")

    segments.append("".join(current_segment))
    rendered_prompt = "[_]".join(segments).strip()
    return rendered_prompt, accepted_answers, segments


def _parse_plain_qml_line(*, line: str, module_id: int, rank: int) -> dict[str, Any]:
    source = line.strip()
    if not source:
        raise QMLError("Question lines cannot be blank.")

    trailing_box = _find_trailing_box(source)
    if trailing_box is not None:
        start, _, opening, content = trailing_box
        prompt = source[:start].rstrip()
        if not prompt:
            raise QMLError("Prompt is required.")
        if opening == "{":
            accepted_answers = [_split_answer_group(value.strip()) for value in split_escaped(content, ",") if value.strip()]
            if len(accepted_answers) < 2:
                raise QMLError("Unordered questions need at least two answer slots.")
            return {
                "module_id": module_id,
                "prompt": prompt,
                "question_type": "multi_text",
                "rank": rank,
                "accepted_answers": accepted_answers,
                "segments": [],
                "bundle_qml": None,
            }

        ordered_slots = [value.strip() for value in split_escaped(content, ",") if value.strip()]
        if len(ordered_slots) > 1:
            return {
                "module_id": module_id,
                "prompt": prompt,
                "question_type": "ordered_multi",
                "rank": rank,
                "accepted_answers": [_split_answer_group(value) for value in ordered_slots],
                "segments": [],
                "bundle_qml": None,
            }

        return {
            "module_id": module_id,
            "prompt": prompt,
            "question_type": "single_text",
            "rank": rank,
            "accepted_answers": [_split_answer_group(content.strip())],
            "segments": [],
            "bundle_qml": None,
        }

    prompt, accepted_answers, segments = _parse_inline_collapse_groups(source)
    return {
        "module_id": module_id,
        "prompt": prompt,
        "question_type": "inline_cloze",
        "rank": rank,
        "accepted_answers": accepted_answers,
        "segments": segments,
        "bundle_qml": None,
    }


def _split_bundle_lines(qml_text: str) -> list[str]:
    lines = [line.rstrip() for line in qml_text.splitlines() if line.strip()]
    if not lines:
        raise QMLError("Bundle must include at least one template line.")
    return lines


def _strip_bundle_outer_wrapper(qml_text: str) -> list[str]:
    lines = _split_bundle_lines(qml_text)
    first = lines[0].lstrip()
    if not first.startswith("{"):
        raise QMLError("Bundle must start with {.")
    first_line = first[1:]
    last_line = lines[-1].rstrip()
    if not last_line.endswith("}"):
        raise QMLError("Bundle must end with }.")
    lines[0] = first_line
    lines[-1] = lines[-1].rstrip()
    lines[-1] = lines[-1][: lines[-1].rfind("}")]
    cleaned = [line.strip() for line in lines if line.strip()]
    if not cleaned:
        raise QMLError("Bundle must include a template and at least one row.")
    return cleaned


def _parse_bundle_template_signature(content: str) -> tuple[list[str], list[str], list[str]]:
    stripped = content.strip()
    if not stripped:
        raise QMLError("Bundle template is required.")

    segments: list[str] = []
    prompt_values: list[str] = []
    current_segment: list[str] = []
    escape = False
    index = 0
    answer_values: list[str] | None = None

    while index < len(stripped):
        char = stripped[index]
        if escape:
            current_segment.append(char)
            escape = False
            index += 1
            continue
        if char == "\\":
            escape = True
            index += 1
            continue
        if char == "{":
            end = index + 1
            cell_chars: list[str] = []
            cell_escape = False
            while end < len(stripped):
                inner = stripped[end]
                if cell_escape:
                    cell_chars.append(inner)
                    cell_escape = False
                    end += 1
                    continue
                if inner == "\\":
                    cell_escape = True
                    end += 1
                    continue
                if inner == "}":
                    break
                cell_chars.append(inner)
                end += 1
            if end >= len(stripped) or stripped[end] != "}":
                raise QMLError("Malformed bundle prompt cell.")
            segments.append("".join(current_segment))
            current_segment = []
            prompt_values.append("".join(cell_chars).strip())
            index = end + 1
            continue
        if char == "[":
            end = index + 1
            cell_chars: list[str] = []
            cell_escape = False
            while end < len(stripped):
                inner = stripped[end]
                if cell_escape:
                    cell_chars.append(inner)
                    cell_escape = False
                    end += 1
                    continue
                if inner == "\\":
                    cell_escape = True
                    end += 1
                    continue
                if inner == "]":
                    break
                cell_chars.append(inner)
                end += 1
            if end >= len(stripped) or stripped[end] != "]":
                raise QMLError("Malformed bundle answer slot.")
            answer_values = _split_answer_group("".join(cell_chars)) if "".join(cell_chars).strip() else []
            segments.append("".join(current_segment))
            if stripped[end + 1 :].strip():
                raise QMLError("Bundle answer slot must be the final element in the template.")
            current_segment = []
            index = len(stripped)
            break
        current_segment.append(char)
        index += 1

    if escape:
        raise QMLError("Dangling escape sequence.")
    if answer_values is None:
        raise QMLError("Bundle template must end with one answer slot [].")
    if not prompt_values and not segments[0].strip():
        raise QMLError("Bundle template needs a real prompt.")
    return segments, prompt_values, answer_values


def _bundle_template_from_segments(segments: list[str]) -> str:
    prompt_parts: list[str] = []
    for index, segment in enumerate(segments[:-1]):
        prompt_parts.append(segment)
        prompt_parts.append("{}")
    prompt_parts.append(segments[-1])
    return "".join(prompt_parts).strip() + " []"


def _parse_bundle_variant_row(line: str, *, prompt_value_count: int) -> dict[str, Any]:
    stripped = line.strip()
    if not stripped:
        raise QMLError("Bundle rows cannot be blank.")

    index = 0
    prompt_values: list[str] = []
    accepted_answers: list[str] | None = None
    for _ in range(prompt_value_count):
        while index < len(stripped) and stripped[index].isspace():
            index += 1
        if index >= len(stripped) or stripped[index] != "{":
            raise QMLError("Bundle row is missing a prompt-value cell.")
        end = index + 1
        cell_chars: list[str] = []
        escape = False
        while end < len(stripped):
            char = stripped[end]
            if escape:
                cell_chars.append(char)
                escape = False
                end += 1
                continue
            if char == "\\":
                escape = True
                end += 1
                continue
            if char == "}":
                break
            cell_chars.append(char)
            end += 1
        if end >= len(stripped) or stripped[end] != "}":
            raise QMLError("Malformed bundle prompt-value cell.")
        prompt_values.append("".join(cell_chars).strip())
        index = end + 1

    while index < len(stripped) and stripped[index].isspace():
        index += 1
    if index >= len(stripped) or stripped[index] != "[":
        raise QMLError("Bundle row must end with an answer cell.")
    end = index + 1
    answer_chars: list[str] = []
    escape = False
    while end < len(stripped):
        char = stripped[end]
        if escape:
            answer_chars.append(char)
            escape = False
            end += 1
            continue
        if char == "\\":
            escape = True
            end += 1
            continue
        if char == "]":
            break
        answer_chars.append(char)
        end += 1
    if end >= len(stripped) or stripped[end] != "]":
        raise QMLError("Malformed bundle answer cell.")
    accepted_answers = _split_answer_group("".join(answer_chars))
    if stripped[end + 1 :].strip():
        raise QMLError("Bundle rows may only contain prompt values followed by one answer cell.")
    return {
        "prompt_values": prompt_values,
        "accepted_answers": accepted_answers,
    }


def build_bundle_qml(prompt: str, bundle_variants: list[dict[str, Any]]) -> str:
    lines = ["{" + prompt.strip()]
    for variant in bundle_variants:
        prompt_cells = " ".join(f"{{{_escape_qml_text(value)}}}" for value in variant.get("prompt_values", []))
        answer_cell = f"[{' | '.join(_escape_qml_text(value) for value in variant.get('accepted_answers', []))}]"
        row = " ".join(part for part in (prompt_cells, answer_cell) if part)
        lines.append(f" {row}")
    if not bundle_variants:
        lines.append("}")
        return "\n".join(lines)
    lines[-1] = lines[-1] + "}"
    return "\n".join(lines)


def _parse_bundle_qml(*, qml_text: str, module_id: int, rank: int) -> dict[str, Any]:
    content_lines = _strip_bundle_outer_wrapper(qml_text)
    template_line = content_lines[0]
    variant_lines = content_lines[1:]
    if not variant_lines:
        raise QMLError("Bundle must include at least one variant row.")

    segments, prompt_values, answer_values = _parse_bundle_template_signature(template_line)
    inline_first_example = any(value != "" for value in prompt_values) or bool(answer_values)
    prompt = _bundle_template_from_segments(segments)
    bundle_variants: list[dict[str, Any]] = []
    if inline_first_example:
        bundle_variants.append(
            {
                "prompt_values": prompt_values,
                "accepted_answers": answer_values,
            }
        )
    else:
        if answer_values:
            raise QMLError("Canonical bundle template answer slot must be empty [].")

    prompt_value_count = len(prompt_values)
    if not inline_first_example:
        prompt_value_count = prompt.count("{}")
    for line in variant_lines:
        bundle_variants.append(_parse_bundle_variant_row(line, prompt_value_count=prompt_value_count))

    canonical_qml = build_bundle_qml(prompt, bundle_variants)
    return {
        "module_id": module_id,
        "prompt": prompt,
        "question_type": "bundle",
        "rank": rank,
        "accepted_answers": [],
        "segments": [],
        "bundle_qml": canonical_qml,
        "bundle_variants": bundle_variants,
    }


def parse_qml_line(*, line: str, module_id: int, rank: int) -> dict[str, Any]:
    source = line.strip()
    if not source:
        raise QMLError("Question lines cannot be blank.")
    if source.startswith("{"):
        return _parse_bundle_qml(qml_text=line, module_id=module_id, rank=rank)
    return _parse_plain_qml_line(line=line, module_id=module_id, rank=rank)


def qml_lines_from_text(qml_text: str) -> list[dict[str, Any]]:
    lines = qml_text.splitlines()
    entries: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        if not raw_line.strip():
            index += 1
            continue
        start_line = index + 1
        if raw_line.lstrip().startswith("{"):
            entry_lines = [raw_line]
            index += 1
            while index < len(lines):
                entry_lines.append(lines[index])
                if lines[index].strip().endswith("}"):
                    index += 1
                    break
                index += 1
            else:
                raise QMLError("Bundle must end with }.")
            qml_entry = "\n".join(entry_lines)
            entries.append(
                {
                    "start_line": start_line,
                    "end_line": start_line + len(entry_lines) - 1,
                    "entry_kind": "bundle",
                    "qml_text": qml_entry,
                }
            )
            continue

        entries.append(
            {
                "start_line": start_line,
                "end_line": start_line,
                "entry_kind": "plain",
                "qml_text": raw_line,
            }
        )
        index += 1

    if not entries:
        raise QMLError("QML must include at least one question entry.")
    return entries


def resolved_bundle_runtime(
    *,
    prompt: str,
    bundle_variants: list[dict[str, Any]],
    rng: Any,
) -> tuple[str, dict[str, Any]]:
    if not bundle_variants:
        raise QMLError("Bundle needs at least one variant.")
    variant = rng.choice(bundle_variants)
    segments = prompt.split("{}")
    if len(segments) - 1 != len(variant.get("prompt_values", [])):
        raise QMLError("Bundle prompt placeholder count does not match variant prompt values.")
    prompt_parts: list[str] = []
    for index, segment in enumerate(segments[:-1]):
        prompt_parts.append(segment)
        prompt_parts.append(variant["prompt_values"][index])
    prompt_parts.append(segments[-1].rsplit("[]", 1)[0])
    resolved_prompt = "".join(prompt_parts).strip()
    return resolved_prompt, {"accepted_answers": [list(variant["accepted_answers"])], "segments": []}


def bundle_variants_from_json(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise QMLError("Bundle variants must be stored as a list.")
    variants: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            raise QMLError("Bundle variants must be objects.")
        prompt_values = item.get("prompt_values", [])
        accepted_answers = item.get("accepted_answers", [])
        if not isinstance(prompt_values, list) or not isinstance(accepted_answers, list):
            raise QMLError("Bundle variant fields must be lists.")
        variants.append(
            {
                "prompt_values": [str(value) for value in prompt_values],
                "accepted_answers": [str(value) for value in accepted_answers],
            }
        )
    return variants
