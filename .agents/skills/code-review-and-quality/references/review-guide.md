# Detailed Review Guide

Read the sections that match the review target. Use the repository [AGENTS.md](../../../../AGENTS.md) and relevant [development](../../../../docs/development.md) sections.

## Context and evidence

- What is the change intended to accomplish, and which plan, requirement, contract, or defect defines success?
- What behavior changes, and what must remain compatible?
- Which files are actually in scope? Which callers, consumers, generated artifacts, migrations, or external boundaries can prove downstream impact?
- Which tests, builds, traces, screenshots, schema checks, or migration checks were run? Record command, exit code, and observed result; do not infer green evidence.

Review the tests first when they exist. Strong tests exercise public behavior, important state transitions, error paths, and regression cases rather than mirroring private implementation details.

## Five-axis questions

### Correctness

- Does the change implement the stated behavior and preserve unrelated behavior?
- Are empty, null, malformed, boundary, retry, concurrency, and partial-failure cases handled where relevant?
- Do state changes remain legal, idempotent, and recoverable?
- Do tests fail for the defect or missing behavior they claim to cover?
- Are errors surfaced honestly, without silent fallback or swallowed failures?

### Readability and simplicity

- Are names specific and consistent with neighboring code?
- Is control flow direct enough to understand without reconstructing hidden state?
- Does each function, component, class, or module have a coherent responsibility?
- Does an abstraction eliminate repeated decisions, or merely move them behind another name?
- Are repeated conditionals evidence of a missing model, policy, or dispatcher?
- Do comments explain durable intent and constraints rather than restating syntax?

### Architecture

- Does dependency flow follow the repository's documented module boundaries?
- Is feature-specific behavior owned by its feature instead of a generic shared layer?
- Are public contracts explicit and stable? Are casts, `any`, excessive optionals, or silent defaults hiding an unclear invariant?
- Does the change preserve API/Demo separation and use the canonical bootstrap wiring?
- Are schema, mapper, generated contract, compatibility, and migration impacts handled together?
- Does a refactor reduce the number of concepts a reader must hold, or only redistribute them?

### Security and privacy

- Is untrusted input validated at the correct boundary and output shaped to the caller's authorization?
- Are authentication, role, ownership, class/student scope, and property-level permissions enforced server-side?
- Could logs, errors, screenshots, traces, URLs, client bundles, or DTOs expose tokens, prompts, full student answers, hidden case facts, or review-only fields?
- Are queries parameterized and external data treated as untrusted?
- Does failure handling avoid weakening protections, silently switching modes, or fabricating AI results?

### Performance

- Does the change add N+1 queries, unbounded loops or fetches, oversized payloads, missing pagination, blocking I/O, or repeated expensive computation?
- Does UI code create unnecessary renders, deep reactive work, layout instability, or large synchronous operations?
- Is there measurement supporting a claimed regression or optimization?
- Does a proposed optimization preserve clarity, correctness, and cross-platform behavior?

## Structural remedies

When structure is the problem, name the move that resolves it:

- replace a conditional chain with a typed model, explicit state machine, or policy;
- collapse duplicate branches into one canonical flow;
- separate orchestration from domain decisions and infrastructure details;
- move feature logic from shared code into the owning module;
- reuse an existing canonical helper instead of adding a near-duplicate;
- make a type or contract boundary explicit so downstream branching disappears;
- remove a pass-through abstraction that adds indirection without meaning;
- extract a cohesive helper, component, or module when a file mixes responsibilities.

Prefer the remedy that removes moving parts over one that spreads the same complexity across more files.

## Change sizing

The upstream guide uses approximately 100 changed lines as easy to review, 300 as often acceptable for one logical change, and 1000 as a signal to split. Treat these only as prompts:

- Generated files, complete deletions, migrations, and mechanical transformations can be large yet reviewable.
- A tiny diff can still create a serious cross-module or authorization defect.
- Split by independently verifiable behavior, ownership boundary, risk, or rollback unit—not merely by line count.
- Keep behavior changes and unrelated refactors separate unless separating them would obscure the actual safe change.

## Severity and review comments

| Level      | Meaning                                                            |
| ---------- | ------------------------------------------------------------------ |
| `Critical` | Data loss, serious security/privacy exposure, or unusable behavior |
| `Required` | Confirmed correctness, contract, architecture, or regression issue |
| `Optional` | Credible improvement that is not needed for this change to be safe |
| `Nit/FYI`  | Non-blocking preference or context                                 |

A useful comment is about code, not its author. It cites evidence, explains impact, and suggests a bounded remedy. Quantify impact only when data supports the number.

## Dependency discipline

When dependencies change, inspect:

1. whether the existing stack already solves the need;
2. maintenance activity, release notes, compatibility, and license;
3. direct and transitive lockfile changes;
4. known advisories without treating an audit tool's severity as unquestionable truth;
5. bundle, runtime, deployment, migration, and rollback impact;
6. focused tests that exercise the behavior supplied by the dependency.

Do not hand-edit a lockfile. Do not require one-dependency-per-change when a tightly coupled upgrade set must move together; require a clear reason and independently reviewable evidence.

## Dead and compatibility code

List code that appears orphaned, but distinguish confirmed dead code from compatibility surfaces, generated artifacts, migration bridges, feature flags, and externally consumed contracts. Search callers and history before recommending removal. Review-only work never authorizes deletion.

## Completion checklist

- [ ] Review target and governing requirement are explicit.
- [ ] Tests and verification evidence were inspected before relying on them.
- [ ] Correctness, readability, architecture, security, and performance were considered proportionally.
- [ ] API/Demo, permissions, sensitive data, contracts, migrations, and cross-platform UI were checked when affected.
- [ ] Findings contain severity, location, evidence, impact, and remediation.
- [ ] Preferences are not mislabeled as defects.
- [ ] Skipped or external checks are identified as gaps.
- [ ] The review makes no unauthorized edits, commits, pushes, merges, deployments, or deletions.

## High-value warning signs

- approving WeChat rendering solely from DOM tests, a successful build, SDK handshake or an uninspected screenshot; see [WeChat validation](../../../../docs/wechat.md);
- claiming API authorization or full coverage equivalence from narrower Demo checks; require explicit gaps and the applicable API/contract evidence.

- approval based only on a green test suite;
- findings without file/line evidence or user-visible impact;
- silent fallback, swallowed errors, or weakened checks used to make validation pass;
- feature logic leaking into shared modules or bypassing public interfaces;
- a refactor that relocates complexity without reducing it;
- a near-duplicate of an existing canonical path;
- bug fixes without meaningful regression coverage;
- dependency or generated-file changes whose diff was not reviewed;
- security-sensitive changes without object/property scope analysis;
- large unreviewed compatibility or migration assumptions;
- an unconditional “looks good” verdict despite missing runtime evidence.
