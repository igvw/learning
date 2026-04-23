import json
from typing import Any

from ..database import DatabaseConnection
from ..qml import build_bundle_qml, bundle_variants_from_json, parse_qml_line, resolved_bundle_runtime
from ..schemas import QuestionDraftIn
from .errors import ValidationError
from .text import json_dumps


def bundle_summary(prompt: str, variants: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "bundle_kind": "single_text",
        "prompt_value_count": prompt.count("{}"),
        "variant_count": len(variants),
    }


def bundle_snapshot_type_config(prompt: str, variants: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **bundle_summary(prompt, variants),
        "bundle_variants": variants,
    }


def bundle_variants_from_type_config(type_config: dict[str, Any]) -> list[dict[str, Any]]:
    variants = type_config.get("bundle_variants", [])
    if not isinstance(variants, list):
        raise ValidationError("Bundle proposal snapshots must store bundle_variants as a list.")
    return [
        {
            "prompt_values": [str(value).strip() for value in variant.get("prompt_values", [])],
            "accepted_answers": [str(value).strip() for value in variant.get("accepted_answers", []) if str(value).strip()],
        }
        for variant in variants
        if isinstance(variant, dict)
    ]


def normalize_bundle_payload(payload: QuestionDraftIn) -> tuple[str, list[dict[str, Any]], str]:
    if payload.question_type != "bundle":
        raise ValidationError("Bundle normalization only applies to bundle questions.")

    if payload.bundle_qml and payload.bundle_qml.strip():
        parsed = parse_qml_line(line=payload.bundle_qml, module_id=payload.module_id, rank=payload.rank)
        return (
            str(parsed["prompt"]).strip(),
            list(parsed["bundle_variants"]),
            str(parsed["bundle_qml"]),
        )

    variants = [
        {
            "prompt_values": [value.strip() for value in variant.prompt_values],
            "accepted_answers": [value.strip() for value in variant.accepted_answers],
        }
        for variant in payload.bundle_variants
    ]
    if not payload.prompt.strip():
        raise ValidationError("Bundle template is required.")
    if not variants:
        raise ValidationError("Bundle needs at least one variant.")
    canonical_qml = build_bundle_qml(payload.prompt.strip(), variants)
    return payload.prompt.strip(), variants, canonical_qml


def upsert_question_bundle(connection: DatabaseConnection, *, question_id: int, variants: list[dict[str, Any]]) -> None:
    connection.execute(
        """
        INSERT INTO question_bundles (question_id, variants_json)
        VALUES (?, ?)
        ON CONFLICT (question_id) DO UPDATE SET variants_json = excluded.variants_json
        """,
        (question_id, json_dumps(variants)),
    )


def delete_question_bundle(connection: DatabaseConnection, *, question_id: int) -> None:
    connection.execute("DELETE FROM question_bundles WHERE question_id = ?", (question_id,))


def question_bundle_variants_by_id(
    connection: DatabaseConnection,
    *,
    question_ids: list[int],
) -> dict[int, list[dict[str, Any]]]:
    if not question_ids:
        return {}
    placeholders = ",".join("?" for _ in question_ids)
    rows = connection.execute(
        f"""
        SELECT question_id, variants_json
        FROM question_bundles
        WHERE question_id IN ({placeholders})
        """,
        tuple(question_ids),
    ).fetchall()
    return {
        int(row["question_id"]): bundle_variants_from_json(row["variants_json"])
        for row in rows
    }


def bundle_qml_from_row(prompt: str, variants_json: str | None) -> str | None:
    if variants_json is None:
        return None
    variants = bundle_variants_from_json(variants_json)
    return build_bundle_qml(prompt, variants)


def bundle_qml_from_type_config(prompt: str, type_config: dict[str, Any]) -> str | None:
    variants = bundle_variants_from_type_config(type_config)
    if not variants:
        return None
    return build_bundle_qml(prompt, variants)


def resolved_bundle_question_runtime(
    *,
    prompt: str,
    variants_json: str | None,
    rng: Any,
) -> tuple[str, dict[str, Any]]:
    if not variants_json:
        raise ValidationError("Bundle-backed questions need a stored bundle definition.")
    return resolved_bundle_runtime(
        prompt=prompt,
        bundle_variants=bundle_variants_from_json(variants_json),
        rng=rng,
    )
