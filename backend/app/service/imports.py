import json
from typing import Any

from ..qml import QMLError, parse_qml_line, qml_lines_from_text
from ..schemas import QuestionDraftIn
from .authoring import (
    create_question,
    delete_question_and_close_rank_gap,
    merge_question_progress,
    revise_question,
)
from .catalog import ensure_leaf_module
from .common import (
    ValidationError,
    answer_blocks,
    build_qml_line,
    question_identity_key,
    question_prompt_key,
    serialize_type_config,
)


def _top_level_root(full_slug: str) -> str:
    return full_slug.split("/", 1)[0]


def _report_text(
    unresolved_rows: list[dict[str, Any]],
    *,
    valid_row_count: int,
    skipped_rows: list[dict[str, Any]],
    relocation_rows: list[dict[str, Any]],
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
    lines.extend(
        f"row {row['row_number']} | {row['status']} | {' -> '.join(match['module_full_slug'] for match in row['matched_questions'])} -> {row['target_module_full_slug']} | {row['qml_line']}"
        for row in relocation_rows
    )

    if lines:
        return "\n".join(lines)
    if valid_row_count:
        return "All remaining rows are valid. Commit to save them."
    return "No importable rows remain."


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


def _target_module_context(connection: Any, module_id: int) -> dict[str, Any]:
    module = ensure_leaf_module(connection, module_id)
    full_slug = str(module["full_slug"])
    return {
        "module_id": module_id,
        "module_full_slug": full_slug,
        "root_slug": _top_level_root(full_slug),
    }


def _existing_questions_in_root(connection: Any, root_slug: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            q.id AS question_id,
            q.module_id,
            m.full_slug AS module_full_slug,
            q.question_type,
            q.prompt,
            q.rank,
            q.type_config_json
        FROM questions AS q
        JOIN modules AS m ON m.id = q.module_id
        WHERE m.full_slug = ? OR m.full_slug LIKE ?
        ORDER BY q.id ASC
        """,
        (root_slug, f"{root_slug}/%"),
    ).fetchall()

    existing_rows: list[dict[str, Any]] = []
    for row in rows:
        parsed_type_config = json.loads(row["type_config_json"])
        existing_rows.append(
            {
                "question_id": row["question_id"],
                "module_id": row["module_id"],
                "module_full_slug": row["module_full_slug"],
                "question_type": row["question_type"],
                "prompt": row["prompt"],
                "rank": row["rank"],
                "type_config": parsed_type_config,
                "prompt_key": question_prompt_key(row["question_type"], row["prompt"], parsed_type_config),
                "identity_key": question_identity_key(row["question_type"], row["prompt"], parsed_type_config),
                "qml_line": build_qml_line(row["question_type"], row["prompt"], parsed_type_config),
                "answer_blocks": answer_blocks(parsed_type_config),
            }
        )
    return existing_rows


def _payload_matches_existing(payload: dict[str, Any], existing_row: dict[str, Any]) -> bool:
    return (
        payload["question_type"] == existing_row["question_type"]
        and payload["prompt"].strip() == existing_row["prompt"].strip()
        and serialize_type_config(QuestionDraftIn(**payload)) == existing_row["type_config"]
    )


def _classify_import_rows(
    connection: Any,
    *,
    module_id: int,
    parsed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    context = _target_module_context(connection, module_id)
    existing_rows = _existing_questions_in_root(connection, context["root_slug"])
    target_prompt_keys = {
        row["prompt_key"]
        for row in existing_rows
        if row["module_id"] == module_id
    }
    same_tree_by_identity: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in existing_rows:
        same_tree_by_identity.setdefault(row["identity_key"], []).append(row)

    for row in parsed_rows:
        if row["issues"]:
            continue
        payload = row["payload"]
        type_config = serialize_type_config(QuestionDraftIn(**payload))
        prompt_key = question_prompt_key(payload["question_type"], payload["prompt"], type_config)
        identity_key = question_identity_key(payload["question_type"], payload["prompt"], type_config)
        row["prompt_key"] = prompt_key
        row["identity_key"] = identity_key

        if prompt_key in target_prompt_keys:
            row["skip_reason"] = "Prompt already exists in this leaf module."
            continue

        matches = [
            existing
            for existing in same_tree_by_identity.get(identity_key, [])
            if existing["module_id"] != module_id
        ]
        if not matches:
            continue

        unchanged = all(_payload_matches_existing(payload, match) for match in matches)
        row["relocation"] = {
            "row_number": row["row_number"],
            "qml_line": row["qml_line"],
            "target_module_full_slug": context["module_full_slug"],
            "status": "merge" if len(matches) > 1 else ("move" if unchanged else "revise"),
            "requires_edit": len(matches) > 1 or not unchanged,
            "ready_without_edit": unchanged,
            "imported_answer_blocks": answer_blocks(type_config),
            "matched_questions": [
                {
                    "question_id": match["question_id"],
                    "module_id": match["module_id"],
                    "module_full_slug": match["module_full_slug"],
                    "qml_line": match["qml_line"],
                    "answer_blocks": match["answer_blocks"],
                }
                for match in matches
            ],
        }
        row["matched_questions"] = matches

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in parsed_rows:
        if row["issues"] or row.get("skip_reason"):
            continue
        groups.setdefault(row["prompt_key"], []).append(row)

    for group_rows in groups.values():
        ordered_rows = sorted(group_rows, key=lambda candidate: candidate["row_number"])
        if len(ordered_rows) > 1:
            for row in ordered_rows[1:]:
                row["skip_reason"] = "Prompt duplicates an earlier row in this upload."
                row.pop("relocation", None)
                row.pop("matched_questions", None)
    return parsed_rows


def _validate_question_import_rows(
    connection: Any,
    *,
    module_id: int,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ensure_leaf_module(connection, module_id)

    normalized_rows = _normalize_import_rows(rows)
    parsed_rows: list[dict[str, Any]] = []
    for row in normalized_rows:
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
    relocation_rows = [row["relocation"] for row in parsed_rows if row.get("relocation")]
    valid_rows = [
        row
        for row in parsed_rows
        if not row["issues"] and not row.get("skip_reason") and row["payload"]
    ]
    result = {
        "ready_to_commit": bool(not unresolved_rows and valid_rows),
        "rows": normalized_rows,
        "valid_row_count": len(valid_rows),
        "skipped_duplicate_count": len(skipped_rows),
        "skipped_rows": skipped_rows,
        "unresolved_rows": unresolved_rows,
        "relocation_rows": relocation_rows,
        "report_text": _report_text(
            unresolved_rows,
            valid_row_count=len(valid_rows),
            skipped_rows=skipped_rows,
            relocation_rows=relocation_rows,
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


def _apply_relocation_row(connection: Any, *, payload: dict[str, Any], matched_questions: list[dict[str, Any]]) -> None:
    survivor = min(matched_questions, key=lambda row: row["question_id"])
    extra_question_ids = [row["question_id"] for row in matched_questions if row["question_id"] != survivor["question_id"]]

    if extra_question_ids:
        merge_question_progress(
            connection,
            survivor_question_id=survivor["question_id"],
            merged_question_ids=extra_question_ids,
        )
        connection.execute(
            f"DELETE FROM user_review_flags WHERE question_id IN ({','.join('?' for _ in [survivor['question_id'], *extra_question_ids])})",
            (survivor["question_id"], *extra_question_ids),
        )
    result = revise_question(
        connection,
        survivor["question_id"],
        QuestionDraftIn(**payload),
        reset_stats=False,
    )
    _ = result
    for question_id in extra_question_ids:
        delete_question_and_close_rank_gap(connection, question_id)


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
        if row.get("matched_questions"):
            _apply_relocation_row(connection, payload=payload.model_dump(), matched_questions=row["matched_questions"])
        else:
            create_question(connection, payload)
        committed_count += 1

    return {
        **result,
        "committed": True,
        "committed_count": committed_count,
    }
