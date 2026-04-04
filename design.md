# Learning App Design

## Overview

This project is a minimalist, modern, keyboard-first web app for learning basic facts through short quizzes. The app stays independent from the learning content itself. Content lives in simple module files, while the app focuses on quiz flow, revision, and progress tracking.

The app uses:

- FastAPI
- Svelte
- SQLite

The overall feel should be clean, lightweight, and fast. The interface should support finishing a quiz without lifting your hands from the keyboard.

## Product Goals

- Keep the app simple.
- Keep app logic separate from module content.
- Support multiple modules and nested submodules.
- Make quiz flow fast and pleasant.
- Make revision and maintenance of questions easy.
- Keep the UI modern and uncluttered.

## Core Concepts

### Modules

Modules are hierarchical, such as `Biology -> Plants`. A user can study a single leaf module or a larger parent bundle. Modules also carry the small amount of metadata needed to vary labels and copy across different content areas.

### Questions

Questions belong to modules and support multiple types. The initial app includes:

- a single-input type where multiple answers may be accepted but only one answer is expected
- an unordered multi-input type where several required answers must be entered but answer order does not matter
- an ordered multi-input type for prompts where the sequence itself matters
- a type where the prompt contains inline blanks to fill in

Questions are editable in place. Numeric ranking exists as a rough importance hint for default ordering.

### Progress

The app tracks quiz sessions and derives per-question progress from those sessions over time. Question content should stay separate from performance data so future per-user progress remains straightforward to add. Multi-input questions may award fractional credit within the question, but each question still contributes one total point to session scoring and aggregate accuracy.

## Content Format

Content should stay easy to generate and edit outside the app.

- module metadata lives in simple YAML files
- questions live in CSV files
- module slugs are inferred from titles

The app should be able to import missing seed content into an existing local database without forcing a reset.

## Starter Content

The first version should include enough seed content to make the quiz, stats, and revision flows feel real during development.

- Seed 2 parent modules with 2 submodules each with 5 questions each (total 20 questions) for testing.
- include every supported question type
- make the sample content varied enough to exercise module hierarchy, rankings, and revision workflows

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

The completed quiz acts as the review surface. There is no need for a separate review page. When the last question is submitted, the finished session should clearly transition into a completed state, focus an obvious way to start another quiz immediately, and allow answered questions to be flagged for revision directly from a compact action in the card header.

### Stats

The stats page shows recent quiz performance and a question table for the selected module scope. Recent performance should be a compact graph of the latest ten sessions for the exact selected module, read left to right from older to newer within that window, with an average reference line. The table should be sortable by its headings, and questions marked for review should stand out through row treatment rather than a dedicated review column.

### Creation And Revision

Question creation and revision should feel straightforward and lightweight. It should be possible to:

- create questions for any supported type
- create a new module inline when needed
- move a question to a different module during revision
- mark whether a revision should reset historical stats

## UX Direction

The app should look modern, dark, and restrained rather than heavy or enterprise-like.

- a visible header with only `Quiz`, `Stats`, and a hamburger menu
- module selection from the hamburger menu with a click-to-expand module tree
- a floating plus button on stats for question creation
- strong keyboard-first interactions throughout
- minimal instructional copy on the quiz page
- mostly neutral dark surfaces, with brighter color used intentionally for actions, correctness feedback, and performance graphs

For question input:

- required multi-answer questions use multiple input boxes
- unordered and ordered multi-input questions are distinct authoring choices
- inline definition questions are answered directly in place
- `Enter` should move the user forward whenever possible
- once a question is submitted, its submit control should disappear

## Testing

The project should include normal Python tests for backend behavior and practical coverage for the main quiz flow. The local project should still be easy to run with `./app.sh`.

## Design Principle

This document stays intentionally high level. It should describe the product clearly without over-specifying the implementation. Schema details, endpoint details, and other low-level decisions can be figured out during implementation.
