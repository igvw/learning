# Learning App API

This document indexes the API surface by capability.

See also:

- [Overview](overview.md)
- [Database](database.md)
- [UI](ui.md)

## Conventions

- all app routes live under `/api`
- request and response bodies are JSON unless otherwise noted
- `question_type` is one of `single_text`, `computed_text`, `multi_text`, `ordered_multi`, `inline_cloze`
- authenticated routes use the server-side session cookie
- demo uses the same route surface, and write routes reject with a demo-mode error without mutating the real database

## Route Groups

- [Authentication and sessions](api/auth.md)
  Healthcheck, first-admin bootstrap, sign-in, sign-out, and demo session entry.
- [Content, accounts, moderation, and questions](api/content.md)
  Modules, users, contribution queues, moderation actions, question authoring, and review flags.
- [Study and stats](api/study.md)
  Quiz-session start/submit behavior, feedback fields, and stats payloads.
- [Imports](api/imports.md)
  QML import format, validation results, and commit behavior.

Use the grouped docs above for detailed request and response behavior.
