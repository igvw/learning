Test authoring workflow:

- Start from the runtime domain boundary: auth, catalog, quiz, stats, moderation, imports, or UI page surface.
- Reuse existing builders and support helpers before duplicating setup payloads.
- Keep broad integration coverage only when the behavior truly spans multiple domains.
- Prefer adding a focused test file over extending an unrelated large suite.
- If a helper exists only to shorten one test, keep it local to that test file.
- When a newer focused test fully replaces an older broad assertion, delete the older assertion instead of keeping duplicate coverage.
- When a feature or code path is removed or deprecated, remove the obsolete tests that only preserve the old behavior.
- If a test-driven behavior change needs docs to stay accurate, make the smallest focused docs update in the owning doc.
