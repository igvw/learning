from typing import Any

from ..qml import QMLError, parse_qml_line, qml_lines_from_text
from ..schemas import QuestionDraftIn
from .authoring import _existing_prompt_keys, create_question
from .catalog import ensure_leaf_module
from .common import ValidationError, question_prompt_key, serialize_type_config


def _report_text(
    unresolved_rows: list[dict[str, Any]],
    *,
    valid_row_count: int,
    skipped_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.extend(
        f"row {row['row_number']} | needs fix | {'; '.join(row['issues'])} | {row['qml_line']}"
        for row in unresolved_rows
    )
    lines.extend(
        f"row {row['row_number']} | skipped duplicate | {row['reason']} | {row['qml_line']}"
        for row in skipped_rows
    )

    if lines:
        return "\n".join(lines)
    if valid_row_count:
        return "All remaining rows are valid. Commit to save them."
    return "No importable rows remain."


def _classify_import_rows(
    connection: Any,
    *,
    module_id: int,
    parsed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_keys = _existing_prompt_keys(connection, module_id)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in parsed_rows:
        if row["issues"]:
            continue
        payload = row["payload"]
        type_config = serialize_type_config(QuestionDraftIn(**payload))
        key = question_prompt_key(payload["question_type"], payload["prompt"], type_config)
        row["prompt_key"] = key
        groups.setdefault(key, []).append(row)

    for key, rows in groups.items():
        ordered_rows = sorted(rows, key=lambda row: row["row_number"])
        if key in existing_keys:
            for row in ordered_rows:
                row["skip_reason"] = "Prompt already exists in this leaf module."
            continue
        if len(ordered_rows) > 1:
            for row in ordered_rows[1:]:
                row["skip_reason"] = "Prompt duplicates an earlier row in this upload."
    return parsed_rows


def _normalize_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValidationError("Import must include at least one question row.")

    normalized_rows: list[dict[str, Any]] = []
    seen_row_numbers: set[int] = set()
    for row in sorted(rows, key=lambda candidate: candidate["row_number"]):
        row_number = int(row["row_number"])
        qml_line = row["qml_line"]
        if row_number in seen_row_numbers:
            raise ValidationError("Row numbers must be unique.")
        if "\n" in qml_line or "\r" in qml_line:
            raise ValidationError("Each QML row must stay on one line.")
        seen_row_numbers.add(row_number)
        normalized_rows.append({"row_number": row_number, "qml_line": qml_line})
    return normalized_rows


def _validate_question_import_rows(
    connection: Any,
    *,
    module_id: int,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ensure_leaf_module(connection, module_id)

    parsed_rows: list[dict[str, Any]] = []
    for row in _normalize_import_rows(rows):
        row_number = row["row_number"]
        qml_line = row["qml_line"]
        issues: list[str] = []
        inferred_type: str | None = None
        payload: dict[str, Any] | None = None
        try:
            payload = parse_qml_line(line=qml_line, module_id=module_id, rank=row_number)
            draft = QuestionDraftIn(**payload)
            inferred_type = draft.question_type
            payload = draft.model_dump()
        except (QMLError, ValueError) as error:
            issues.append(str(error))
        parsed_rows.append(
            {
                "row_number": row_number,
                "qml_line": qml_line,
                "inferred_type": inferred_type,
                "payload": payload,
                "issues": issues,
            }
        )

    parsed_rows = _classify_import_rows(connection, module_id=module_id, parsed_rows=parsed_rows)
    unresolved_rows = [
        {
            "row_number": row["row_number"],
            "qml_line": row["qml_line"],
            "issues": row["issues"],
            "inferred_type": row["inferred_type"],
        }
        for row in parsed_rows
        if row["issues"]
    ]
    skipped_rows = [
        {
            "row_number": row["row_number"],
            "qml_line": row["qml_line"],
            "reason": row["skip_reason"],
            "inferred_type": row["inferred_type"],
        }
        for row in parsed_rows
        if row.get("skip_reason")
    ]
    valid_rows = [row for row in parsed_rows if not row["issues"] and not row.get("skip_reason") and row["payload"]]
    result = {
        "ready_to_commit": bool(not unresolved_rows and valid_rows),
        "valid_row_count": len(valid_rows),
        "skipped_duplicate_count": len(skipped_rows),
        "skipped_rows": skipped_rows,
        "unresolved_rows": unresolved_rows,
        "report_text": _report_text(
            unresolved_rows,
            valid_row_count=len(valid_rows),
            skipped_rows=skipped_rows,
        ),
        "committed": False,
        "committed_count": 0,
    }
    return result, valid_rows


def validate_question_import(
    connection: Any,
    *,
    module_id: int,
    qml_text: str | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        normalized_rows = qml_lines_from_text(qml_text) if qml_text is not None else _normalize_import_rows(rows or [])
    except QMLError as error:
        raise ValidationError(str(error)) from error
    result, _ = _validate_question_import_rows(connection, module_id=module_id, rows=normalized_rows)
    return result


def commit_question_import(
    connection: Any,
    *,
    module_id: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    result, valid_rows = _validate_question_import_rows(connection, module_id=module_id, rows=rows)
    if result["unresolved_rows"]:
        return result

    committed_count = 0
    for row in valid_rows:
        payload = QuestionDraftIn(**row["payload"])
        create_question(connection, payload)
        committed_count += 1

    return {
        **result,
        "committed": True,
        "committed_count": committed_count,
    }
