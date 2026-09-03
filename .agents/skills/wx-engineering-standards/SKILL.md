---
name: wx-engineering-standards
description: Apply this repository's engineering constraints to feature changes, fixes, refactors, and code review; route work to authoritative docs and safe, evidence-based verification. Do not use for standalone prose edits unless they change project engineering instructions.
---

# WX Engineering Standards

Use this project-local skill when a change can affect source code, module boundaries, API/Demo behavior, data, authentication, generated contracts, migrations, tests, or delivery evidence. Do not use it for an isolated prose change unless that prose changes project engineering instructions.

## Non-negotiable routing

1. Read the repository [AGENTS.md](../../../AGENTS.md) and run a read-only `git status` before editing. Preserve existing tracked and untracked work; do not reset, clean, restore deleted files, commit, push, merge, or change global Codex settings.
2. Read only the authoritative documents needed for the change: [architecture](../../../docs/architecture.md), [data layer](../../../docs/data-layer.md), [development](../../../docs/development.md), [database](../../../docs/database.md), [security](../../../docs/security.md), [deployment](../../../docs/deployment.md), and relevant [ADR](../../../docs/adr/0001-data-layer-contracts.md). For module changes, also read [frontend public interfaces](../../../docs/frontend-public-interfaces.md) or [backend module map](../../../docs/backend-module-map.md). The update-plan files describe plans and evidence, not current implementation.
3. Separate the two states in notes and decisions:
   - **当前事实**: verified files, paths, commands, behavior, and observed evidence in this checkout.
   - **计划目标**: T01–T07 proposals or commands that are not yet implemented or accepted. Never turn a planned command into a required passing check before its owner supplies evidence.
4. Identify whether the change affects a public API/schema, generated OpenAPI/types/fixtures, migration, API/Demo mode selection, authorization/data scope, secrets/logging, or test-database lifecycle. Keep compatibility and rollback impact explicit.
5. Apply the smallest safe verification route. Pure Markdown does not require database, backend, or E2E execution. T01 is accepted locally: backend pytest entry points use the launcher-owned temporary database; `backend:test:safety` and `backend:test:migrations` are available; `contract:check` generates in a system temporary directory and does not rewrite source snapshots. `contract:generate` remains explicitly write-capable. T02 remote CI, branch protection and target Node 22/Python 3.12 evidence are not implied by local scripts. Re-run the safety and migration checks when changing their bootstrap, ownership, engine initialization, migrations, or E2E launcher.
6. Record commands, exit codes, evidence paths, skipped checks with reasons, risks, and rollback information using [the delivery template](references/delivery-template.md). A file's existence is not acceptance evidence.

## Change routing

- Frontend page/UI: use the architecture and data-layer boundaries; pages import `features/*/public.ts` only. Check formatting, lint, types, and focused tests when the environment is safe.
- Frontend data, identity, or storage: also inspect `src/bootstrap/wiring.ts`, API/Demo selection, runtime validation, user scoping, cache/session behavior, contract consumers, and run `node scripts/frontend-boundaries.mjs` for structural work.
- Backend route, service, model, schema, migration, permission, or AI change: inspect security and database rules first. Route work through `app/modules/<module>/{api,application,domain,infrastructure}`, `public.py` and `wiring.py`; `app/api|models|schemas|services` are compatibility only. Run `python backend/scripts/check_boundaries.py` for module work.
- Cross-module R05 rule: only `api` or `wiring` may directly import another module's `api`; application/domain/infrastructure must use a stable `public.py` contract or explicit port. Do not solve a violation with an allowlist unless the documented boundary owner authorizes it.
- Cross-module, dependency, build, or CI change: use the actual scripts and gates present in this checkout. `backend:test:safety`, `backend:test:migrations`, `scripts/frontend-boundaries.mjs`, and `backend/scripts/check_boundaries.py` are implemented; the latter two have no `package.json` aliases. Remote CI and branch protection remain external evidence requirements.
- Review-only request: report observable risks and missing evidence; do not make fixes unless requested.

## Safety invariants

- API errors must not silently switch to Demo; `VITE_APP_MODE` is chosen at bootstrap and authorization stays server-side.
- Client bundles and logs must not contain server secrets, tokens, full prompts, full student answers, or hidden case data.
- Generated contract files are changed through their generation workflow, together with source schema/routes, mappers, and tests; never hand-edit generated output.
- Database migrations and seed operations target only an explicitly confirmed, managed non-production resource. Never use a user's development database for destructive test experiments.
- External deployment, remote history, credentials, plugins, and global settings require separate explicit authorization.

## Minimal self-check

From the repository root, run:

```text
python .agents/skills/wx-engineering-standards/scripts/self_check.py
```

This is a local, read-only structure/link/state-label and routing-reference check. It does not run backend tests, migrations, E2E, network calls, or contract generation. It must pass before this skill is treated as structurally usable; it does not prove project commands, S2 evidence, T01/T02 acceptance, remote CI, or production readiness.
