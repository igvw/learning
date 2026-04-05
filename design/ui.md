# Learning App UI Design

This document describes the current UI structure and the interaction rules that matter most to the product.

See also:

- [Overview](overview.md)
- [Database](database.md)
- [API](api.md)

## App Structure

The app is organized around three primary pages plus a shared module menu:

- `Quiz`
- `Stats`
- `Admin`
- hamburger menu for module selection

The header keeps navigation visible at all times, and the current module scope flows through quiz and stats behavior.

## Module Menu

The hamburger menu is the shared module-scope control.

Current behavior:

- modules are shown as a tree
- clicking a parent module selects that scope and opens its branch
- clicking a leaf module selects it and closes the menu
- top-level branches auto-collapse when the user switches to a different top-level branch
- the menu no longer exposes a dedicated `All Modules` action

This keeps broad module switching quick without leaving the tree overly expanded.

## Quiz Page

The quiz page is the default route and remains the most keyboard-sensitive part of the app.

Current behavior:

- a quiz session locks a fixed set of questions when it starts
- only one unanswered question is active at a time
- answered cards remain visible above the active card
- `Enter` moves through multi-input answers and submits from the final input
- correct answers tint the card and submitted fields green
- incorrect answers tint the card red and highlight only the wrong submitted fields red
- expected answers are shown only when the response was not fully correct
- multi-input questions may show partial progress such as `2/3` while still counting as one total question in the session score

Instruction handling:

- for a leaf-module quiz, the selected module instruction can be shown once as shared context
- for parent-scope quizzes, a child module instruction may be shown on question cards when needed

Completed-session behavior:

- the completed state acts as the review surface
- the next-quiz action is surfaced prominently and focused automatically
- answered questions can be flagged for revision from a compact icon action in the card header

## Stats Page

The stats page combines recent performance with question maintenance.

Current behavior:

- recent performance is shown as a compact graph of the latest ten sessions for the exact selected module
- the graph runs left to right from older to newer within that latest-ten window
- an average reference line remains visible without persistent label text
- the question table is sortable by its column headings
- review-flagged questions are highlighted at the row level
- the floating plus button opens question creation from stats

The stats page is therefore both a reporting surface and the main entry point for question editing.

## Admin Page

The admin page is for shared-content administration rather than quiz use.

Current behavior:

- module creation supports slash-separated paths such as `norwegian/vocabulary/nouns_to_english`
- existing path segments are reused, giving the form `mkdir -p` behavior
- an optional parent module can act as the base path
- module instruction is entered here and applies to the final created module node
- CSV import starts only after selecting a leaf module as the target

This keeps module creation and import concerns clearly separate from quiz-taking and stats review.

## Import Drawer

The import drawer is the UI for staged CSV uploads.

Current behavior:

- it opens from Admin after a leaf module is selected
- the target module and its instruction are shown at the top
- the user can paste CSV text or choose a CSV file
- the first step validates the upload and creates a server-backed import session

When unresolved rows remain:

- the UI shows a validation report textbox
- unresolved rows appear in a row-based editor with immutable line numbers
- hovering the line-number gutter reveals a delete action for discarding that row
- the user edits rows in place and revalidates them
- rows that validate successfully disappear from the unresolved list and remain staged

Commit behavior:

- commit is only available once the session is ready
- no questions are saved until commit succeeds
- newly conflicting rows can still block commit and return the session to repair mode

This flow is intentionally stricter than a simple bulk upload so content can be repaired without creating partial imports.
