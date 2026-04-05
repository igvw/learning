# Learning App Overview

This is the main product-level design document for the app. For subsystem details, see the focused docs on the [database](database.md), [API](api.md), and [UI](ui.md).

## Overview

This project is a minimalist, modern, keyboard-first web app for learning facts, language, and procedural knowledge through short quizzes. The app stays intentionally separate from the learning content itself. Content can start from seed files and can also be extended through in-app admin flows, while the app focuses on module hierarchy, quiz flow, progress tracking, and lightweight maintenance.

The app uses:

- FastAPI
- Svelte
- SQLite

The overall feel should stay clean, lightweight, and fast. The interface should support finishing a quiz without lifting your hands from the keyboard.

## Product Goals

- Keep the app simple.
- Keep app logic separate from module content.
- Support multiple modules and nested submodules.
- Make quiz flow fast and pleasant.
- Make revision and maintenance of questions easy.
- Keep the UI modern and uncluttered.

## Core Concepts

### Modules

Modules are hierarchical, such as `Norwegian -> Vocabulary -> nouns_to_english`. Users can study a single leaf module or a larger parent bundle. Modules also carry a small amount of metadata, including optional `instruction` text that lets a leaf module provide context for short prompts like `hund` without repeating the full question wording on every row.

### Questions

Questions belong to modules and support multiple types:

- a single-input type where multiple answers may be accepted but only one answer is expected
- an unordered multi-input type where several required answers must be entered but answer order does not matter
- an ordered multi-input type for prompts where the sequence itself matters
- a type where the prompt contains inline blanks to fill in

Questions are editable in place. Rank acts as the current default ordering hint for authoring, quiz selection, and stats.

### Progress

The app tracks quiz sessions and derives per-question progress from those sessions over time. Question content stays separate from performance data so future per-user progress remains straightforward to add. Multi-input questions may award fractional credit within the question, but each question still contributes one total point to session scoring and aggregate accuracy.

### Content And Import

Content should stay easy to generate and edit outside the app, but the current product also supports in-app administration:

- seed content can still come from module files in the repo
- modules can be created in the Admin page
- CSV question uploads now run through staged import sessions before commit

The design intentionally keeps import and quiz behavior separate: import work prepares shared content, while quiz sessions record progress against that content.

## Main Screens

### Quiz

The quiz is the default page. It presents a fixed number of questions and grows vertically as answers are submitted.

The experience should feel immediate:

- only one unanswered question is active at a time, but submitted questions stay visible above it
- `Enter` advances through multi-input questions and submits from the final input
- correct submissions tint the question card green and mark the submitted answer fields green
- incorrect submissions tint the question card red and mark only the incorrect submitted fields red
- expected answers are shown below a question only when the answer was not fully correct, and they appear in a neutral suggestion box
- multi-input questions may show partial progress such as `2/3` on the card while still counting as one total question in the session score

The completed quiz acts as the review surface. When the last question is submitted, the finished session should clearly transition into a completed state, focus an obvious way to start another quiz immediately, and allow answered questions to be flagged for revision directly from a compact action in the card header.

### Stats

The stats page shows recent quiz performance and a question table for the selected module scope. Recent performance is a compact graph of the latest ten sessions for the exact selected module, read left to right from older to newer within that window, with an average reference line. The table is sortable by its headings, and questions marked for review stand out through row treatment rather than a dedicated review column.

Stats also remain the main question-maintenance surface. Creating and revising questions should stay straightforward and lightweight from this page.

### Admin

The Admin page owns shared-content administration:

- creating modules, including slash-separated module paths
- setting module instruction text
- choosing a leaf module as a question-import target
- opening the staged CSV import flow

This keeps module creation and import concerns out of the quiz and stats flows.

## UX Direction

The app should look modern, dark, and restrained rather than heavy or enterprise-like.

- a visible header with `Quiz`, `Stats`, `Admin`, and a hamburger menu
- module selection from the hamburger menu with a click-to-expand module tree
- a floating plus button on stats for question creation
- strong keyboard-first interactions throughout
- minimal instructional copy on the quiz page
- mostly neutral dark surfaces, with brighter color used intentionally for actions, correctness feedback, and performance graphs

For question input:

- required multi-answer questions use multiple input boxes
- unordered and ordered multi-input questions are distinct authoring choices
- inline cloze questions are answered directly in place
- `Enter` should move the user forward whenever possible
- once a question is submitted, its submit control should disappear

## Testing

The project should include normal Python tests for backend behavior and practical coverage for the main quiz flow, stats interactions, admin module creation, and staged CSV imports. The local project should still be easy to run with `./app.sh`.

## Design Principle

This document stays intentionally high level. It describes the product clearly without over-specifying the implementation. The supporting docs cover the current database, API, and UI shape in more detail without turning into raw source dumps.
