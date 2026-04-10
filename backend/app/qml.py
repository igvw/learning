import ast
import random
import re
from typing import Any


class QMLError(ValueError):
    pass


_ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.+)\s*$")
_RANGE_RE = re.compile(r"\[(\d+)-(\d+)\]")
_TOKEN_RE = re.compile(r"\$([^$]+)\$")


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


def contains_variable_binding(text: str) -> bool:
    return any(_ASSIGNMENT_RE.match(match.group(1).strip()) for match in _TOKEN_RE.finditer(text))


def format_numeric(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


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


def _parse_inline_cloze(line: str) -> tuple[str, list[list[str]], list[str]]:
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


def parse_qml_line(*, line: str, module_id: int, rank: int) -> dict[str, Any]:
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
            }

        return {
            "module_id": module_id,
            "prompt": prompt,
            "question_type": "computed_text" if contains_variable_binding(prompt) else "single_text",
            "rank": rank,
            "accepted_answers": [_split_answer_group(content.strip())],
            "segments": [],
        }

    prompt, accepted_answers, segments = _parse_inline_cloze(source)
    return {
        "module_id": module_id,
        "prompt": prompt,
        "question_type": "inline_cloze",
        "rank": rank,
        "accepted_answers": accepted_answers,
        "segments": segments,
    }


def qml_lines_from_text(qml_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_number, raw_line in enumerate(qml_text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        rows.append({"row_number": row_number, "qml_line": raw_line})
    if not rows:
        raise QMLError("QML must include at least one question line.")
    return rows


def _replace_ranges(expression: str, *, rng: random.Random) -> str:
    def replacer(match: re.Match[str]) -> str:
        start = int(match.group(1))
        end = int(match.group(2))
        if end < start:
            raise QMLError("Variable ranges must run from low to high.")
        return str(rng.randint(start, end))

    return _RANGE_RE.sub(replacer, expression)


def _safe_eval(expression: str, env: dict[str, float]) -> float:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise QMLError(f"Invalid expression: {expression}") from error

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise QMLError(f"Unknown variable: {node.id}")
            return float(env[node.id])
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = evaluate(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if right == 0:
                raise QMLError("Division by zero is not allowed.")
            return left / right
        raise QMLError("Expressions only support numbers, variables, +, -, *, /, and parentheses.")

    return evaluate(tree)


def _evaluate_expression(expression: str, *, env: dict[str, float], rng: random.Random) -> float:
    return _safe_eval(_replace_ranges(expression, rng=rng), env)


def render_prompt_and_answers(
    *,
    prompt: str,
    accepted_answers: list[list[str]],
    rng: random.Random | None = None,
) -> tuple[str, list[list[str]]]:
    generator = rng or random.Random()
    env: dict[str, float] = {}

    def prompt_replacer(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        assignment = _ASSIGNMENT_RE.match(content)
        if assignment:
            value = _evaluate_expression(assignment.group(2).strip(), env=env, rng=generator)
            env[assignment.group(1)] = value
            return format_numeric(value)
        try:
            return format_numeric(_evaluate_expression(content, env=env, rng=generator))
        except QMLError:
            return content

    rendered_prompt = _TOKEN_RE.sub(prompt_replacer, prompt)

    def answer_replacer(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        return format_numeric(_evaluate_expression(content, env=env, rng=generator))

    rendered_answers = [
        [_TOKEN_RE.sub(answer_replacer, answer) for answer in answer_group]
        for answer_group in accepted_answers
    ]
    return rendered_prompt, rendered_answers
