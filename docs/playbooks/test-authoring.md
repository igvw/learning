# Test Authoring

Use this workflow when adding or refactoring tests.

1. Start from the runtime domain boundary: auth, catalog, quiz, stats, moderation, imports, or UI page surface.
2. Reuse existing builders/support helpers before duplicating setup payloads.
3. Keep broad integration coverage only when the behavior truly spans multiple domains.
4. Prefer adding a focused test file over extending an unrelated large suite.
5. If a helper exists only to shorten one test, keep it local to that test file.
6. When a newer focused test fully replaces an older broad assertion, delete the older assertion instead of keeping duplicate coverage.
