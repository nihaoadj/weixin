---
name: code-review-and-quality
description: Review a specified code change when the user requests or delegates code review. Do not use for routine implementation or test execution.
---

# Code Review and Quality

Load for an explicit review request or delegated review task. Running tests or implementing a change alone does not trigger this skill.

Review the supplied diff, staged changes, branch/commit range or named files. Keep unrelated dirty-worktree changes outside the review. Do not modify files or external state unless fixes are requested.

Use [AGENTS.md](../../../AGENTS.md) and the relevant [development](../../../docs/development.md) sections for project contracts. Inspect intended behavior, consumers and relevant tests; expand only to establish an impact. Consider correctness, simplicity, architecture, security, performance and verification in proportion to the change.

For detailed review criteria, severity definitions or dependency/compatibility changes, read the relevant [review-guide](references/review-guide.md) sections. UI findings use [wx-frontend-ui](../wx-frontend-ui/SKILL.md) without turning a review into redesign.

Lead with actionable findings ordered by severity. Each needs a precise location, evidence, affected behavior and a bounded remedy. Separate required defects from preferences; passing tests alone do not prove contracts or rendering. If no material defect is confirmed, say so and name meaningful verification gaps.

Adapted from Addy Osmani's `agent-skills` at `6ca0cd7db39b41b1c37e26d335c507ee92382c6d`; retain the bundled [MIT license](LICENSE.txt).
