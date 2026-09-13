---
name: code-review-and-quality
description: Review a concrete code change or diff in this repository across correctness, readability, architecture, security, performance, verification, and dependency discipline. Use when the user explicitly asks for code review, a pre-merge quality assessment, or review of completed changes. Do not use for ordinary implementation, standalone UI design audits, or general project-rule routing.
---

# Code Review and Quality

Review changes with evidence, prioritize material defects, and leave the final decision with the user. This project adaptation preserves the multi-axis review discipline from Addy Osmani's `agent-skills` at commit `6ca0cd7db39b41b1c37e26d335c507ee92382c6d`; the bundled [MIT license](LICENSE.txt) applies to the adapted upstream material.

## Authority and scope

1. Read the repository [AGENTS.md](../../../AGENTS.md) and use [WX Engineering Standards](../wx-engineering-standards/SKILL.md) for project boundaries, safe evidence collection, and verification routing. Those sources override generic review heuristics.
2. Resolve the review target before inspecting it: a supplied diff, staged changes, a branch/commit range, or explicitly named files. Do not treat unrelated dirty-worktree changes as part of the review.
3. A review request is read-only unless the user also asks for fixes. Do not modify or delete files, install dependencies, commit, push, merge, deploy, or change external state as part of review alone.
4. For a standalone visual or UX audit, use [WX Frontend UI](../wx-frontend-ui/SKILL.md). When a code review includes UI changes, apply its project-specific cross-platform and accessibility bar without turning the review into a redesign.

## Review workflow

1. **Understand intent.** Identify the governing plan, specification, contract, bug report, or stated behavior. Separate verified facts from assumptions and missing evidence.
2. **Bound the diff.** Inspect the requested change, its callers and consumers, relevant tests, and nearby authoritative patterns. Expand scope only where needed to prove an impact.
3. **Review tests before implementation.** Check whether tests express the intended behavior, cover important error and boundary paths, and would fail for the suspected regression.
4. **Apply the five axes.** Review correctness, readability and simplicity, architecture, security, and performance. Also verify the evidence story and dependency changes when present.
5. **Classify findings.** Use `Critical`, `Required`, `Optional`, or `Nit/FYI`. A finding needs a concrete location, evidence, user or system impact, and the smallest credible remedy.
6. **Verify the verification.** Distinguish checks observed in this checkout from checks merely claimed, skipped, external, or unsafe to run.

For a substantive review, read [the detailed review guide](references/review-guide.md). Use only the sections relevant to the change.

## Five-axis standard

- **Correctness:** Match requirements and contracts; check state transitions, null/empty/boundary cases, error paths, concurrency, idempotency, and whether tests prove the behavior.
- **Readability and simplicity:** Prefer explicit control flow, accurate names, cohesive responsibilities, and abstractions that remove rather than relocate complexity. Do not reward fewer lines when meaning becomes harder to see.
- **Architecture:** Enforce the repository's public interfaces, dependency direction, API/Demo separation, generated-contract workflow, and ownership boundaries. Reuse the canonical path instead of normalizing a near-duplicate.
- **Security:** Examine trust boundaries, input/output shaping, authentication, authorization and object scope, secrets, sensitive logs, injection, hidden student/case data, and unsafe external calls. Report only evidence-backed issues.
- **Performance:** Look for plausible regressions such as N+1 queries, unbounded work, excessive payloads, missing pagination, unnecessary renders, or blocking hot paths. Require measurement before prescribing optimization when impact is uncertain.

## Findings-first output

Lead with actionable findings ordered by severity and impact. Keep file and line references tight. Do not bury defects under summaries or cosmetic preferences.

Each finding should state:

- severity and a concise title;
- exact file/line and evidence;
- why the behavior is wrong or risky;
- affected user, contract, data, or runtime;
- smallest safe remediation and any verification needed.

After findings, include only a short assumptions/questions section and a verification-gap summary when useful. If no material finding is confirmed, say so explicitly and name remaining unverified risks. Never manufacture findings to make a review look substantial.

## Review judgment

- Tests passing is necessary evidence, not proof that architecture, security, readability, or product behavior is correct.
- Change-size numbers in the upstream guide are inspection signals, not project gates. Judge cohesion, generated output, mechanical refactors, and reviewability before recommending a split.
- Separate required defects from preferences. Style is blocking only when it violates an authoritative project rule or materially harms correctness or maintainability.
- Propose structural movement, not vague complaints: identify the layer, owner, boundary, model, or helper that should change.
- Identify dead or compatibility code, but do not remove it during review. Confirm callers, migration commitments, and user authorization first.
- Human decisions and documented project exceptions override generic preferences; record the trade-off without silently weakening an actual safety boundary.
