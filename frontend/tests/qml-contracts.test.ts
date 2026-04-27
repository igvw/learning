import { readFileSync } from 'node:fs';

import { describe, expect, it } from 'vitest';

import { parsePendingImportRows } from '../src/lib/import-review';
import {
  buildQmlLine,
  canonicalizeBundleEditorText,
  parseBundleEditorText,
  parseQmlLine,
  type ParsedQmlQuestion
} from '../src/lib/qml';

type BundleVariantContract = {
  prompt_values: string[];
  accepted_answers: string[];
};

type QuestionContract = {
  prompt: string;
  question_type: string;
  accepted_answers: string[][];
  segments: string[];
  bundle_qml: string | null;
  bundle_variants: BundleVariantContract[];
};

type ValidParseCase = {
  name: string;
  input: string;
  canonical_qml: string;
  canonical_editor_text?: string;
  expected: QuestionContract;
};

type ImportEntryCase = {
  name: string;
  input: string;
  expected_entries: Array<{
    start_line: number;
    end_line: number;
    entry_kind: 'plain' | 'bundle';
    qml_text: string;
  }>;
};

type InvalidParseCase = {
  name: string;
  input: string;
};

type QmlContracts = {
  valid_parse_cases: ValidParseCase[];
  valid_import_entry_cases: ImportEntryCase[];
  invalid_parse_cases: InvalidParseCase[];
};

const contracts = JSON.parse(
  readFileSync('../tests/fixtures/qml-contracts.json', 'utf8')
) as QmlContracts;

function normalizeQuestion(parsed: ParsedQmlQuestion): QuestionContract {
  const bundleVariants =
    parsed.question_type === 'bundle' && parsed.bundle_qml
      ? parseBundleEditorText(parsed.bundle_qml).variants
      : [];
  return {
    prompt: parsed.prompt,
    question_type: parsed.question_type,
    accepted_answers: parsed.accepted_answers,
    segments: parsed.segments,
    bundle_qml: parsed.bundle_qml ?? null,
    bundle_variants: bundleVariants
  };
}

describe('QML parser contracts', () => {
  it('parses valid QML cases the same way as the shared contract', () => {
    for (const testCase of contracts.valid_parse_cases) {
      const parsed = parseQmlLine(testCase.input);

      expect(normalizeQuestion(parsed), testCase.name).toEqual(testCase.expected);
    }
  });

  it('builds canonical QML from valid parse cases', () => {
    for (const testCase of contracts.valid_parse_cases) {
      const parsed = parseQmlLine(testCase.input);

      expect(buildQmlLine(parsed), testCase.name).toBe(testCase.canonical_qml);
      if (testCase.canonical_editor_text) {
        expect(canonicalizeBundleEditorText(testCase.input), testCase.name).toBe(testCase.canonical_editor_text);
      }
    }
  });

  it('splits valid import text into the shared entry shape', () => {
    for (const testCase of contracts.valid_import_entry_cases) {
      expect(parsePendingImportRows(testCase.input), testCase.name).toEqual(testCase.expected_entries);
    }
  });

  it('rejects invalid QML cases from the shared contract', () => {
    for (const testCase of contracts.invalid_parse_cases) {
      expect(() => parseQmlLine(testCase.input), testCase.name).toThrow();
    }
  });
});
