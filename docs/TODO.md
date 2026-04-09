# TODO

## Priority 1: Security And Access

- Harden all user-authored text against injection attacks:
  sanitize and safely render QML, prompts, answers, module titles, handles, and display names
- Add input limits and parser hardening for QML imports, question editing, and answer submission
- Add passwords and proper authentication for users
- Add guest, user, and admin modes with real authorization boundaries
- Restrict admin-only actions:
  module creation, question creation/revision, imports, and user management should not be open to ordinary users
- Add production security basics for public deployment:
  secure session handling, CSRF protection if cookie auth is used, tighter CORS, security headers, and rate limiting

## Priority 2: Runtime And Deployment

- Upgrade the runtime and tooling from Python 3.12 to Python 3.14
- Refactor backend code to make good use of newer Python features once the upgrade lands
- Host the app on a public URL with HTTPS and production deployment hardening
- Add backup and restore guidance for hosted deployments

## Priority 3: Product And Authoring Follow-Ups

- Config-driven behavior
- Spaced repetition algorithm variants
- Export bundles
- QML v2: ghost-text syntax for authoring hints and richer examples

## Priority 4: Eternal Slimdown 
Do this after any major piece of feature additions

- Slim down data model further
- Slim down API further
- Slim down UI further
