# Learning App UI

This document indexes the UI structure and main interaction surfaces.

See also:

- [Overview](overview.md)
- [Database](database.md)
- [API](api.md)

## App Structure

The app has three main pages plus shared navigation:

- `Quiz`
- `Stats`
- `Admin`
- hamburger menu for module selection
- authenticated account badge and logout menu in the header

## Shared UI Rules

- the hamburger menu controls module scope for study and authoring flows
- clicking a parent module selects that scope and opens its branch
- clicking a leaf module selects it and closes the menu
- top-level branches auto-collapse when switching roots
- current-state UI docs describe behavior in present tense and do not keep historical comparison notes

## Page Docs

- [Authentication and account entry](ui/auth.md)
- [Quiz page](ui/quiz.md)
- [Stats page](ui/stats.md)
- [Manage page](ui/manage.md)
- [Import drawer and upload flow](ui/imports.md)
