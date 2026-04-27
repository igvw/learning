import json
import unittest
from pathlib import Path
from typing import Any

from backend.app.qml import QMLError, build_bundle_qml, parse_qml_line, qml_lines_from_text
from backend.app.service.questions import build_qml_line


CONTRACT_PATH = Path(__file__).parents[1] / "fixtures" / "qml-contracts.json"


def _load_contracts() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text())


def _normalize_question(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt": parsed["prompt"],
        "question_type": parsed["question_type"],
        "accepted_answers": parsed["accepted_answers"],
        "segments": parsed["segments"],
        "bundle_qml": parsed.get("bundle_qml"),
        "bundle_variants": parsed.get("bundle_variants", []),
    }


class QmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contracts = _load_contracts()

    def test_valid_qml_parse_contracts(self) -> None:
        for case in self.contracts["valid_parse_cases"]:
            with self.subTest(case=case["name"]):
                parsed = parse_qml_line(line=case["input"], module_id=10, rank=20)

                self.assertEqual(_normalize_question(parsed), case["expected"])

    def test_valid_qml_canonical_build_contracts(self) -> None:
        for case in self.contracts["valid_parse_cases"]:
            with self.subTest(case=case["name"]):
                parsed = parse_qml_line(line=case["input"], module_id=10, rank=20)
                if parsed["question_type"] == "bundle":
                    self.assertEqual(parsed["bundle_qml"], case["canonical_qml"])
                    self.assertEqual(
                        build_bundle_qml(parsed["prompt"], parsed["bundle_variants"]),
                        case["canonical_qml"],
                    )
                    continue

                self.assertEqual(
                    build_qml_line(
                        parsed["question_type"],
                        parsed["prompt"],
                        {
                            "accepted_answers": parsed["accepted_answers"],
                            "segments": parsed["segments"],
                        },
                    ),
                    case["canonical_qml"],
                )

    def test_valid_import_entry_contracts(self) -> None:
        for case in self.contracts["valid_import_entry_cases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(qml_lines_from_text(case["input"]), case["expected_entries"])

    def test_invalid_qml_parse_contracts(self) -> None:
        for case in self.contracts["invalid_parse_cases"]:
            with self.subTest(case=case["name"]):
                with self.assertRaises(QMLError):
                    parse_qml_line(line=case["input"], module_id=10, rank=20)
