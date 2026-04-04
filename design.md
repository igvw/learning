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

- a type where multiple answers may be accepted but only one answer is expected
- a type where several required answers must all be entered
- a type where the prompt contains inline blanks to fill in

Questions are revisable. Revisions should preserve history while allowing the active version to move forward cleanly. Numeric ranking exists as a rough importance hint for default ordering.

### Progress

The app tracks quiz sessions and per-question progress over time. It should be easy to see how often a question is asked, how often it is answered correctly, and which questions need revision.

## Content Format

Content should stay easy to generate and edit outside the app.

- module metadata lives in simple YAML files
- questions live in CSV files
- module slugs are inferred from titles

The app should be able to import missing seed content into an existing local database without forcing a reset.

## Main Screens

### Quiz

The quiz is the default page. It presents a fixed number of questions and grows vertically as answers are submitted.

The experience should feel immediate:

- submitted questions stay visible
- correct answers are highlighted in green
- incorrect answers are highlighted in red
- correct answers are shown below each answered question

The completed quiz acts as the review surface. There is no need for a separate review page. When the last question is submitted, the finished session should clearly transition into a completed state and offer an obvious way to start another quiz immediately.

### Stats

The stats page shows recent quiz performance and a question table for the selected module scope. It should also surface questions marked for review so maintenance work is easy to find.

### Creation And Revision

Question creation and revision should feel straightforward and lightweight. It should be possible to:

- create questions for any supported type
- create a new module inline when needed
- move a question to a different module during revision
- review prior versions of a question
- mark whether a revision should reset historical stats

## UX Direction

The app should look modern, dark, and restrained rather than heavy or enterprise-like.

- a visible header with only `Quiz`, `Stats`, and a hamburger menu
- module selection from the hamburger menu
- a floating plus button on stats for question creation
- strong keyboard-first interactions throughout
- minimal instructional copy on the quiz page

For question input:

- required multi-answer questions use multiple input boxes
- inline definition questions are answered directly in place
- once a question is submitted, its submit control should disappear

## Testing

The project should include normal Python tests for backend behavior and practical coverage for the main quiz flow. The local project should still be easy to run with `./app.sh`.

## Design Principle

This document stays intentionally high level. It should describe the product clearly without over-specifying the implementation. Schema details, endpoint details, and other low-level decisions can be figured out during implementation.
