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

The header also includes the authenticated account badge and logout menu.

## Module Menu

The hamburger menu controls module scope.

Current behavior:

- modules are shown as a tree
- clicking a parent selects that scope and opens its branch
- clicking a leaf selects it and closes the menu
- top-level branches auto-collapse when switching roots

## Authentication

The app now starts with an auth screen instead of a user switcher.

Current behavior:

- if no admin exists yet, the auth screen shows first-admin bootstrap
- normal accounts sign in by handle and password
- demo mode starts an ephemeral showcase session with no real writes
- the top-right badge shows the current account and logout action

## Quiz Page

The quiz page is the keyboard-first study surface.

Current behavior:

- one unanswered question is active at a time
- answered cards remain visible
- `Enter` moves through multi-input answers and submits from the last field
- correct answers tint the card green
- incorrect answers tint the card red and show all accepted answers in the grey feedback box
- correct answers that used a non-default accepted alternative expand that slot’s disabled input to all accepted answers
- correct answers that used the default accepted answer do not show a separate neutral feedback box
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
- retry-eligibility graph
- first-time questions answered by day over the last 7 local days
- sortable question table
- `Review only` checkbox that filters that same table between non-review and review-flagged rows
- floating create-question action

The question table currently focuses on:

- rank
- prompt
- logical bucket
- last seen
- attempts
- correctness

Current table behavior:

- when unchecked, the table shows only non-review rows
- when checked, the table shows only review-flagged rows
- summary cards and graphs stay based on the full module scope while the table is filtered
- unverified uploaded questions and personal revision overlays show badges in the question table
- chart layout is two rows:
  `Latest quiz performance` with `Entry states` on the top row, then `Spaced repetition stages`, `Retry eligibility`, and `First-time questions answered` below
- `Spaced repetition stages` shows the full fixed ladder through `60d`
- clicking `Spaced repetition stages` opens a detail overlay with a due-day heatmap:
  bucket columns `<1d`, `1d`, `3d`, `7d`, `14d`, `30d`, `60d`; day rows from `Today` through the latest scheduled fixed-stage day within the next 60 local days; overdue items collapse into `Today`
- `Retry eligibility` groups immediate availability into `<1`, keeps day buckets `1` through `7`, and groups longer availability into `>7`
- clicking `Retry eligibility` opens a detail overlay with the next 24 local clock-hour buckets for the current `<1` group, shown in 24-hour time, and rolling weekly windows for the current `>7` group
- review rows stay orange when shown in the filtered table
- hot rows are shaded red in two intensities in the main table
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
- revision mode can delete the current question after confirmation
- regular-user revision mode on verified questions becomes a personal proposal flow:
  module and rank stay locked, and delete becomes `Request Delete`
- admins still edit verified questions directly

Incorrect-answer history currently shows:

- answer text
- count
- latest incorrect time

## Admin / Manage Page

The third route is now role-aware instead of always being a pure admin page.

Current behavior:

- admins see:
  account creation and password reset
  global module editing
  QML import
  moderation summary cards for pending modules, pending uploaded questions, and question revision/delete proposals
- admins open each moderation category in its own overlay instead of keeping the full queue inline on the page
- the pending uploaded questions overlay groups rows by module and supports bulk approve/reject per module table
- request-changes stays a row-by-row action, and pending modules plus revision/delete proposals remain individually reviewed
- regular users see:
  pending leaf-module creation under verified parents
  QML import for pending question uploads
  editable own pending leaf modules
  a `My contributions` list with statuses and review notes
- demo shows the same contribution surface in a disabled/showcase form

## Import Drawer

The import drawer is a review-and-commit drawer for one leaf module.

Current behavior:

- paste or load QML text
- validate rows into one review table
- show exact duplicate counts in the summary instead of cluttering the table
- show duplicate, relocation, invalid, and conflict rows together in the same table
- keep original physical line numbers visible and color-coded
- let editable rows change QML directly in the table
- show answer chips grouped by answer slot
- color-code answer chips by source:
  - current answer
  - imported answer
  - manually added answer
- persist the import session in `sessionStorage` so refresh restores the drawer state
- save with one button and determinate chunk progress
- allow the drawer to be hidden while an upload keeps running in the current tab
- show a compact header upload-status pill that reopens the drawer

Current import-save behavior:

- save submits the current edited rows
- the frontend saves committable rows in 50-row chunks
- while a chunked upload is active, the review rows become read-only status rows
- partial success keeps the drawer open, removes already committed rows, and revalidates the remainder
- blocking rows stay highlighted red until edited or removed
- in demo mode the import entry points stay visible, but saving is blocked
