# AI Usage Report

## Scope of this report

This report covers the **GitHub-preparation session only**: repository
hygiene (`.gitignore`, environment templates), a README accuracy pass,
`docs/assumptions.md`, this file, and verification commands. Detailed
per-phase prompt logs for Phases 1–6 were **not recorded in this session**,
so they are not reconstructed here — anything beyond this session would be
fabrication.

## What the AI assistant did in this session

- Inspected the repository tree, existing `.gitignore`, environment files,
  `docker-compose.yml`, frontend sources, docs, and test inventory.
- Replaced the root `.gitignore` with a consolidated ruleset (secrets,
  Python, Node, IDE/OS, logs, local DB dumps) and removed the redundant
  nested `frontend/.gitignore` (Vite boilerplate, covered by the root file).
- Normalized `backend/.env.example` placeholders to `<password>` /
  `<generate-a-secure-secret>` style; left `docker-compose.yml` defaults
  untouched (they are documented compose fallbacks, not secrets).
- Rewrote the stale Phase-1-scoped top of `README.md` (features, stack
  versions verified against `package.json`/`requirements.txt`,
  architecture diagram, folder structure, setup commands verified against
  `app/main.py`, `app/seed.py`, `pytest.ini`), marked the seed login as
  development-only in two places, and recorded the verified 166-test result.
- Wrote `docs/assumptions.md` strictly from session-verified facts.
- Ran read-only verification: secret grep over sources (clean), pytest
  collection, application import, and Git status/ignore checks below.

## Prompts and corrections (this session, summarized honestly)

- No AI-generated code required correction: the one malformed shell
  invocation (a `Select-String` quoting error) was a tooling slip, retried
  successfully with an equivalent command. No incorrect implementation
  output occurred because no implementation was produced — only docs,
  ignore rules, and checks.

## Validation

- `pytest --collect-only` passes (structure intact; full suite last
  verified green at 166 tests during Phase 6).
- `git status` / `git check-ignore` confirm `backend/.env` and caches are
  ignored while `backend/alembic/versions/` is tracked (see final report).
