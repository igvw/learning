import json
from typing import Any

from ..qml import QMLError, parse_qml_line, qml_lines_from_text
from ..schemas import QuestionDraftIn
from .auth import Actor
from .authoring import (
    apply_import_revision,
    create_question_append_only,
    relocate_question_for_import,
)
from .bundles import bundle_qml_from_row, normalize_bundle_payload
from .catalog import ensure_leaf_module
from .errors import ValidationError
from .questions import answer_blocks, build_qml_line, serialize_type_config, stored_prompt_key


def _top_level_root(full_slug: str) -> str:
    return full_slug.split("/", 1)[0]


def _report_text(*, valid_row_count: int, review_rows: list[dict[str, Any]], exact_duplicate_count: int) -> str:
    summary_bits: list[str] = []
    if valid_row_count:
        summary_bits.append(f"{valid_row_count} ready to commit")
    if review_rows:
        summary_bits.append(f"{len(review_rows)} rows need review")
    if exact_duplicate_count:
        summary_bits.append(f"{exact_duplicate_count} exact duplicates omitted")
    if summary_bits:
        return " | ".join(summary_bits)
    return "No importable rows remain."


def _result_payload(
    *,
    normalized_rows: list[dict[str, Any]],
    valid_rows: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    exact_duplicate_count: int,
) -> dict[str, Any]:
    return {
        "ready_to_commit": bool(valid_rows) and not any(row["blocking"] for row in review_rows),
        "rows": normalized_rows,
        "valid_row_count": len(valid_rows),
        "committable_start_lines": [row["start_line"] for row in valid_rows],
        "exact_duplicate_count": exact_duplicate_count,
        "review_rows": review_rows,
        "report_text": _report_text(
            valid_row_count=len(valid_rows),
            review_rows=review_rows,
            exact_duplicate_count=exact_duplicate_count,
        ),
        "committed": False,
        "committed_count": 0,
    }


def _normalize_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValidationError("Import must include at least one question row.")

    normalized_rows: list[dict[str, Any]] = []
    seen_start_lines: set[int] = set()
    for row in sorted(rows, key=lambda candidate: (candidate["start_line"], candidate["end_line"])):
        start_line = int(row["start_line"])
        end_line = int(row["end_line"])
        entry_kind = row["entry_kind"]
        qml_text = row["qml_text"]
        if start_line in seen_start_lines:
            raise ValidationError("Import entry start lines must be unique.")
        if end_line < start_line:
            raise ValidationError("Import entry end lines must be greater than or equal to start lines.")
        if entry_kind == "plain" and ("\n" in qml_text or "\r" in qml_text):
            raise ValidationError("Plain QML entries must stay on one line.")
        seen_start_lines.add(start_line)
        normalized_rows.append(
            {
                "start_line": start_line,
                "end_line": end_line,
                "entry_kind": entry_kind,
                "qml_text": qml_text,
            }
        )
    return normalized_rows


def _target_module_context(connection: Any, module_id: int) -> dict[str, Any]:
    module = ensure_leaf_module(connection, module_id)
    full_slug = str(module["full_slug"])
    return {
        "module_id": module_id,
        "module_full_slug": full_slug,
        "root_slug": _top_level_root(full_slug),
    }


def _existing_questions_for_prompt_keys(
    connection: Any,
    *,
    module_id: int,
    root_slug: str,
    prompt_keys: set[str],
) -> list[dict[str, Any]]:
    if not prompt_keys:
        return []

    placeholders = ",".join("?" for _ in prompt_keys)
    rows = connection.execute(
        f"""
        SELECT
            q.id AS question_id,
            q.module_id,
            m.full_slug AS module_full_slug,
            q.question_type,
            q.prompt,
            q.prompt_key,
            q.rank,
            q.type_config_json,
            bundles.variants_json
        FROM questions AS q
        JOIN modules AS m ON m.id = q.module_id
        LEFT JOIN question_bundles AS bundles ON bundles.question_id = q.id
        WHERE q.prompt_key IN ({placeholders})
          AND (q.module_id = ? OR m.full_slug = ? OR m.full_slug LIKE ?)
        ORDER BY q.id ASC
        """,
        (*sorted(prompt_keys), module_id, root_slug, f"{root_slug}/%"),
    ).fetchall()

    existing_rows: list[dict[str, Any]] = []
    for row in rows:
        parsed_type_config = json.loads(row["type_config_json"])
        entry_kind = "bundle" if row["question_type"] == "bundle" else "plain"
        qml_text = (
            bundle_qml_from_row(str(row["prompt"]), row["variants_json"])
            if row["question_type"] == "bundle"
            else build_qml_line(row["question_type"], row["prompt"], parsed_type_config)
        )
        existing_rows.append(
            {
                "question_id": row["question_id"],
                "module_id": row["module_id"],
                "module_full_slug": row["module_full_slug"],
                "question_type": row["question_type"],
                "prompt": row["prompt"],
                "rank": row["rank"],
                "type_config": parsed_type_config,
                "prompt_key": row["prompt_key"],
                "entry_kind": entry_kind,
                "qml_text": qml_text,
                "bundle_qml": qml_text if entry_kind == "bundle" else None,
                "answer_blocks": [] if entry_kind == "bundle" else answer_blocks(parsed_type_config),
            }
        )
    return existing_rows


def _payload_matches_existing(payload: dict[str, Any], existing_row: dict[str, Any]) -> bool:
    if payload["question_type"] == "bundle":
        left_prompt, _, left_qml = normalize_bundle_payload(QuestionDraftIn(**payload))
        _ = left_prompt
        return left_qml == existing_row.get("bundle_qml")
    return (
        payload["question_type"] == existing_row["question_type"]
        and payload["prompt"].strip() == existing_row["prompt"].strip()
        and serialize_type_config(QuestionDraftIn(**payload)) == existing_row["type_config"]
    )


def _payload_matches_payload(left_payload: dict[str, Any], right_payload: dict[str, Any]) -> bool:
    if left_payload["question_type"] == "bundle" or right_payload["question_type"] == "bundle":
        if left_payload["question_type"] != right_payload["question_type"]:
            return False
        _, _, left_qml = normalize_bundle_payload(QuestionDraftIn(**left_payload))
        _, _, right_qml = normalize_bundle_payload(QuestionDraftIn(**right_payload))
        return left_qml == right_qml
    left_draft = QuestionDraftIn(**left_payload)
    right_draft = QuestionDraftIn(**right_payload)
    return (
        left_draft.question_type == right_draft.question_type
        and left_draft.prompt.strip() == right_draft.prompt.strip()
        and serialize_type_config(left_draft) == serialize_type_config(right_draft)
    )


def _existing_reference(existing_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": existing_row["question_id"],
        "module_id": existing_row["module_id"],
        "module_full_slug": existing_row["module_full_slug"],
        "entry_kind": existing_row["entry_kind"],
        "qml_text": existing_row["qml_text"],
        "answer_blocks": existing_row["answer_blocks"],
    }


def _upload_reference(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": None,
        "module_id": None,
        "module_full_slug": f"Earlier upload row {row['start_line']}",
        "entry_kind": row["entry_kind"],
        "start_line": row["start_line"],
        "end_line": row["end_line"],
        "qml_text": row["qml_text"],
        "answer_blocks": row["imported_answer_blocks"],
    }


def _combined_answer_blocks(references: list[dict[str, Any]]) -> list[str]:
    combined: list[str] = []
    for reference in references:
        for block in reference["answer_blocks"]:
            if block not in combined:
                combined.append(block)
    return combined


def _review_row(
    *,
    start_line: int,
    end_line: int,
    entry_kind: str,
    qml_text: str,
    status: str,
    status_text: str,
    editable: bool,
    blocking: bool,
    imported_answer_blocks: list[str],
    matched_questions: list[dict[str, Any]] | None = None,
    target_module_full_slug: str | None = None,
) -> dict[str, Any]:
    references = matched_questions or []
    return {
        "start_line": start_line,
        "end_line": end_line,
        "entry_kind": entry_kind,
        "qml_text": qml_text,
        "status": status,
        "status_text": status_text,
        "editable": editable,
        "blocking": blocking,
        "target_module_full_slug": target_module_full_slug,
        "current_answer_blocks": _combined_answer_blocks(references),
        "imported_answer_blocks": imported_answer_blocks,
        "matched_questions": references,
    }


def _classify_existing_and_relocation_rows(
    *,
    context: dict[str, Any],
    module_id: int,
    parsed_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    target_rows_by_prompt: dict[str, list[dict[str, Any]]] = {}
    same_tree_rows_by_prompt: dict[str, list[dict[str, Any]]] = {}

    for existing in existing_rows:
        if existing["module_id"] == module_id:
            target_rows_by_prompt.setdefault(existing["prompt_key"], []).append(existing)
        else:
            same_tree_rows_by_prompt.setdefault(existing["prompt_key"], []).append(existing)

    for row in parsed_rows:
        if row["issues"]:
            row["review_row"] = _review_row(
                start_line=row["start_line"],
                end_line=row["end_line"],
                entry_kind=row["entry_kind"],
                qml_text=row["qml_text"],
                status="invalid",
                status_text=f"Invalid QML: {'; '.join(row['issues'])}",
                editable=True,
                blocking=True,
                imported_answer_blocks=row["imported_answer_blocks"],
            )
            continue

        payload = row["payload"]
        target_matches = target_rows_by_prompt.get(row["prompt_key"], [])
        if target_matches:
            references = [_existing_reference(match) for match in target_matches]
            if len(target_matches) > 1:
                row["review_row"] = _review_row(
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    entry_kind=row["entry_kind"],
                    qml_text=row["qml_text"],
                    status="conflict",
                    status_text="This prompt already matches multiple questions in the target leaf. Edit it to a unique prompt or remove the row.",
                    editable=True,
                    blocking=True,
                    imported_answer_blocks=row["imported_answer_blocks"],
                    matched_questions=references,
                )
                continue

            match = target_matches[0]
            if payload["question_type"] != match["question_type"]:
                row["review_row"] = _review_row(
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    entry_kind=row["entry_kind"],
                    qml_text=row["qml_text"],
                    status="conflict",
                    status_text="This prompt already exists in the target leaf with a different question type. Edit it to a unique prompt or remove the row.",
                    editable=True,
                    blocking=True,
                    imported_answer_blocks=row["imported_answer_blocks"],
                    matched_questions=references,
                )
                continue

            if _payload_matches_existing(payload, match):
                row["exact_duplicate"] = True
                continue

            row["review_row"] = _review_row(
                start_line=row["start_line"],
                end_line=row["end_line"],
                entry_kind=row["entry_kind"],
                qml_text=row["qml_text"],
                status="duplicate",
                status_text="This prompt already exists in the target leaf. Commit will revise the existing question in place unless you edit the row first.",
                editable=True,
                blocking=False,
                imported_answer_blocks=row["imported_answer_blocks"],
                matched_questions=references,
            )
            row["commit_action"] = {
                "kind": "revise_existing",
                "question_id": match["question_id"],
            }
            continue

        same_tree_matches = same_tree_rows_by_prompt.get(row["prompt_key"], [])
        if not same_tree_matches:
            row["commit_action"] = {"kind": "create"}
            continue

        references = [_existing_reference(match) for match in same_tree_matches]
        if len(same_tree_matches) > 1:
            row["review_row"] = _review_row(
                start_line=row["start_line"],
                end_line=row["end_line"],
                entry_kind=row["entry_kind"],
                qml_text=row["qml_text"],
                status="conflict",
                status_text="This prompt already matches multiple questions elsewhere in the same module tree. Edit it to a unique prompt or remove the row.",
                editable=True,
                blocking=True,
                imported_answer_blocks=row["imported_answer_blocks"],
                matched_questions=references,
                target_module_full_slug=context["module_full_slug"],
            )
            continue

        match = same_tree_matches[0]
        if payload["question_type"] != match["question_type"]:
            row["review_row"] = _review_row(
                start_line=row["start_line"],
                end_line=row["end_line"],
                entry_kind=row["entry_kind"],
                qml_text=row["qml_text"],
                status="conflict",
                status_text=f"This prompt already exists in {match['module_full_slug']} with a different question type. Edit it to a unique prompt or remove the row.",
                editable=True,
                blocking=True,
                imported_answer_blocks=row["imported_answer_blocks"],
                matched_questions=references,
                target_module_full_slug=context["module_full_slug"],
            )
            continue

        if _payload_matches_existing(payload, match):
            row["review_row"] = _review_row(
                start_line=row["start_line"],
                end_line=row["end_line"],
                entry_kind=row["entry_kind"],
                qml_text=row["qml_text"],
                status="info",
                status_text=f"Exact match already exists in {match['module_full_slug']}. Commit will move it to {context['module_full_slug']}.",
                editable=False,
                blocking=False,
                imported_answer_blocks=row["imported_answer_blocks"],
                matched_questions=references,
                target_module_full_slug=context["module_full_slug"],
            )
        else:
            row["review_row"] = _review_row(
                start_line=row["start_line"],
                end_line=row["end_line"],
                entry_kind=row["entry_kind"],
                qml_text=row["qml_text"],
                status="relocation",
                status_text=f"This prompt already exists in {match['module_full_slug']}. Commit will move and revise that question in {context['module_full_slug']}.",
                editable=True,
                blocking=False,
                imported_answer_blocks=row["imported_answer_blocks"],
                matched_questions=references,
                target_module_full_slug=context["module_full_slug"],
            )
        row["commit_action"] = {
            "kind": "relocate_existing",
            "question_id": match["question_id"],
            "source_module_id": match["module_id"],
        }
    return parsed_rows


def _classify_same_upload_duplicates(parsed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in parsed_rows:
        if row["issues"] or row.get("exact_duplicate") or not row.get("payload"):
            continue
        review_row = row.get("review_row")
        if review_row and review_row["status"] == "conflict":
            continue
        groups.setdefault(row["prompt_key"], []).append(row)

    for group_rows in groups.values():
        ordered_rows = sorted(group_rows, key=lambda candidate: candidate["start_line"])
        leader = ordered_rows[0]
        for row in ordered_rows[1:]:
            if _payload_matches_payload(row["payload"], leader["payload"]):
                row["exact_duplicate"] = True
                row.pop("review_row", None)
                row.pop("commit_action", None)
                continue
            row["review_row"] = _review_row(
                start_line=row["start_line"],
                end_line=row["end_line"],
                entry_kind=row["entry_kind"],
                qml_text=row["qml_text"],
                status="duplicate",
                status_text=f"This row duplicates earlier upload row {leader['start_line']} with different answers. Edit it to a unique prompt or remove the row.",
                editable=True,
                blocking=True,
                imported_answer_blocks=row["imported_answer_blocks"],
                matched_questions=[_upload_reference(leader)],
            )
            row.pop("commit_action", None)
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
        qml_text = row["qml_text"]
        issues: list[str] = []
        inferred_type: str | None = None
        payload: dict[str, Any] | None = None
        type_config: dict[str, Any] | None = None
        imported_answer_blocks: list[str] = []
        prompt_key: str | None = None
        try:
            payload = parse_qml_line(line=qml_text, module_id=module_id, rank=row["start_line"])
            draft = QuestionDraftIn(**payload)
            inferred_type = draft.question_type
            payload = draft.model_dump()
            type_config = serialize_type_config(draft)
            imported_answer_blocks = [] if draft.question_type == "bundle" else answer_blocks(type_config)
            prompt_key = stored_prompt_key(draft.question_type, draft.prompt, type_config)
        except (QMLError, ValueError) as error:
            issues.append(str(error))
        parsed_rows.append(
            {
                "start_line": row["start_line"],
                "end_line": row["end_line"],
                "entry_kind": row["entry_kind"],
                "qml_text": qml_text,
                "inferred_type": inferred_type,
                "payload": payload,
                "type_config": type_config,
                "prompt_key": prompt_key,
                "imported_answer_blocks": imported_answer_blocks,
                "issues": issues,
            }
        )

    context = _target_module_context(connection, module_id)
    prompt_keys = {row["prompt_key"] for row in parsed_rows if row["prompt_key"]}
    existing_rows = _existing_questions_for_prompt_keys(
        connection,
        module_id=module_id,
        root_slug=context["root_slug"],
        prompt_keys=prompt_keys,
    )
    parsed_rows = _classify_existing_and_relocation_rows(
        context=context,
        module_id=module_id,
        parsed_rows=parsed_rows,
        existing_rows=existing_rows,
    )
    parsed_rows = _classify_same_upload_duplicates(parsed_rows)

    review_rows = [row["review_row"] for row in parsed_rows if row.get("review_row")]
    exact_duplicate_count = sum(1 for row in parsed_rows if row.get("exact_duplicate"))
    valid_rows = [row for row in parsed_rows if row.get("commit_action")]
    result = _result_payload(
        normalized_rows=normalized_rows,
        valid_rows=valid_rows,
        review_rows=review_rows,
        exact_duplicate_count=exact_duplicate_count,
    )
    return result, valid_rows


def _commit_import_rows(connection: Any, *, module_id: int, valid_rows: list[dict[str, Any]], actor: Actor | None = None) -> int:
    _ = module_id
    committed_count = 0

    for row in valid_rows:
        action = row["commit_action"]
        payload = QuestionDraftIn(**row["payload"])
        if action["kind"] == "create":
            create_question_append_only(connection, payload, actor=actor)
        elif action["kind"] == "revise_existing":
            apply_import_revision(connection, question_id=action["question_id"], payload=payload)
        else:
            relocate_question_for_import(
                connection,
                question_id=action["question_id"],
                payload=payload,
            )
        committed_count += 1

    return committed_count


def validate_question_import(
    connection: Any,
    *,
    module_id: int,
    qml_text: str | None = None,
    rows: list[dict[str, Any]] | None = None,
    actor: Actor | None = None,
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
    actor: Actor | None = None,
) -> dict[str, Any]:
    result, valid_rows = _validate_question_import_rows(connection, module_id=module_id, rows=rows)
    if any(review_row["blocking"] for review_row in result["review_rows"]):
        return result
    if not valid_rows:
        return result

    committed_count = _commit_import_rows(connection, module_id=module_id, valid_rows=valid_rows, actor=actor)

    return {
        **result,
        "committed": True,
        "committed_count": committed_count,
    }
