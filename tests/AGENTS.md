Tests local rules:

- Start from the runtime domain boundary: auth, catalog, quiz, stats, moderation, imports, or UI page surface.
- Reuse existing builders and support helpers before duplicating setup payloads.
- Keep broad integration coverage only when the behavior truly spans multiple domains.
- Prefer a focused test file over extending an unrelated large suite.
- Keep one-off helpers local to the test file that needs them.
- Delete superseded tests and assertions when newer focused coverage replaces them.
