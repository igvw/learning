# Learning App UI

This document describes the current UI structure and main interaction rules.

See also:

- [Overview](overview.md)
- [Database](database.md)
- [API](api.md)

## App Structure

The app has three main pages plus a shared module menu:

- `Quiz`
- `Stats`
- `Admin`
- hamburger menu for module selection

The header also includes the active-user badge and switcher.

## Module Menu

The hamburger menu controls module scope.

Current behavior:

- modules are shown as a tree
- clicking a parent selects that scope and opens its branch
- clicking a leaf selects it and closes the menu
- top-level branches auto-collapse when switching roots

## User Switching

The top-right user badge opens a small switcher menu.

Current behavior:

- badge color is stable per user
- switching users changes quiz history, review flags, stats, and scheduling
- if no active user exists, quiz and stats point the user to Admin
- user creation happens in Admin

## Quiz Page

The quiz page is the keyboard-first study surface.

Current behavior:

- one unanswered question is active at a time
- answered cards remain visible
- `Enter` moves through multi-input answers and submits from the last field
- correct answers tint the card green
- incorrect answers tint the card red and show neutral expected-answer boxes
- the completed session becomes the review surface

Completed-session behavior:

- start-another-quiz action is prominent
- review actions live directly on answered cards
- correctly answered cards can be hidden to focus review

## Stats Page

The stats page combines reporting and question maintenance.

Current behavior:

- recent session performance graph
- spaced-repetition stages graph
- entry-state graph
- sortable question table
- floating create-question action

The question table currently focuses on:

- rank
- prompt
- logical bucket
- last seen
- attempts
- correctness

Visual treatment:

- review-flagged rows are orange
- hot rows are shaded red in two intensities
- logical bucket and hotness are separated intentionally

## Revision Drawer

The revision drawer is the question editing surface.

Current behavior:

- dense single-card layout for question details
- one module selector, not a duplicate module-path display
- prompt, type, rank, and accepted answers grouped tightly
- aggregated incorrect-answer history shown at the bottom in a compact table
- create mode defaults the module selector to the current hamburger-selected scope
- create mode uses a `Priority` selector (`High`, `Mid`, `Low`) instead of raw rank
- create mode keeps a live editable QML box in sync with the structured fields

Incorrect-answer history currently shows:

- answer text
- count
- latest incorrect time

## Admin Page

The Admin page owns shared-content administration.

Current behavior:

- slash-path module creation with `mkdir -p` behavior
- module instruction entry
- user creation
- QML import target selection
- import defaults to the current hamburger-selected module and blocks until a leaf is chosen

## Import Drawer

The import drawer is a stateless repair-and-commit flow.

Current behavior:

- paste or load QML text
- validate lines
- fix only malformed lines
- duplicates are skipped automatically
- commit only the kept valid rows

The UI keeps original physical line numbers locally so import repair can stay stateless.
