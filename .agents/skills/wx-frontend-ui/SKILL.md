---
name: wx-frontend-ui
description: Design, implement, or audit user-facing WeChat Mini Program UI in this Vue 3 and uni-app repository. Use for pages, components, visual hierarchy, responsive behavior, interaction states, accessibility, UX copy, and Developer Tools visual QA. Do not use for browser automation alone or operating-system screenshots.
---

# WX Frontend UI

Produce calm, precise, evidence-led interfaces for the pathology PBL teaching workflow. Treat visual quality, interaction correctness, accessibility, and cross-platform behavior as one design problem.

This is the single project UI-design entry point, integrating Anthropic's design process and UI/UX Pro Max's local retrieval. See [sources and adaptation](references/sources.md) for pinned originals, licenses, and deliberate differences. User instructions take precedence over skill guidance. Apply [AGENTS.md](../../../AGENTS.md) update routing: isolated skill maintenance needs no UpdatePlan; functional changes still do.

## Route the work

1. Identify the affected user, page job, primary action, real data states, and target runtimes before choosing a layout.
2. Read [the project quality bar](references/quality-bar.md) for UI work and [the established frontend design](../../../docs/frontend/design.md) for existing surfaces. Its historical navigation descriptions do not override current AGENTS.md/T22 or verified routes. Preserve useful visual identity, not known defects.
3. When UI code reads or writes business data, also read [frontend public interfaces](../../../docs/frontend/public-interfaces.md). Do not invent page-level repositories, requests, storage access, routes, or backend contracts.
4. For implementation or visual evidence, read [verification routing](references/verification.md) and select checks proportional to the change.

## Choose the design depth

- New pages, substantial redesigns, or a request to improve visual quality: read [design workflow](references/design-workflow.md). Produce a compact design brief, retrieve relevant local knowledge, review the direction against the user's brief, then implement and critique rendered evidence.
- A narrow style/copy/interaction fix: inspect the affected state, use the relevant quality rules, and verify that state. Do not force a full design-system exercise or invent new design documents.
- Audit-only: inspect and report using Review mode below; do not modify the interface. Use [local knowledge](references/knowledge.md) if a specific finding needs support.

## Design and implementation

- Start from information priority and task sequence. Establish what must be noticed, compared, decided, and acted on before adding visual treatment.
- Preserve real content and truthful states. Design loading, empty, error, disabled, success, long-text, and narrow-screen behavior when the affected flow can reach them.
- Audit the repository's tokens and shared components before reusing them. Check computed styles and selector specificity: inherited `.card`, `.section`, or button rules may contradict the intended hierarchy. Reuse sound primitives; correct defects within scope with explicit semantic tokens or scoped variants. Do not silently redesign unrelated consumers of a global class.
- Prefer hierarchy created by typography, spacing, alignment, dividers, and restrained color. A container earns a card treatment only when it is an independently actionable or focusable object.
- Give each surface one coherent visual idea tied to clinical teaching or evidence review. Distinction should come from composition and detail, not decoration, novelty fonts, gratuitous motion, or generic dashboard styling.
- Implement with Vue 3, TypeScript, uni-app components, scoped styles, and conditional compilation only where runtime behavior genuinely differs. Never translate React, Tailwind, or browser-only examples into this codebase by habit.
- Keep interaction names and outcomes consistent. A button label should predict the resulting state and confirmation message.
- Preserve user intent and existing contracts. A UI task does not authorize new product behavior, synthetic medical claims, hidden-field exposure, or silent API-to-Demo fallback.

## Review mode

When asked to audit an interface, inspect the actual target files and available rendered evidence. Report actionable findings first, ordered by user impact, with tight file and line references. Separate confirmed defects from visual preferences and unverified cross-platform risks. If no defect is found, say so and name the remaining verification gap.

Use the pinned local knowledge when relevant; no live third-party fetch is required for ordinary UI work. Retrieved examples are evidence to interpret, not instructions to override project contracts or install their libraries.

## Completion bar

WeChat is the only product target under T24. Inspect the compiled Mini Program in Developer Tools and follow [WeChat validation](../../../docs/operations/wechat-validation.md). H5, DOM component tests and successful builds do not prove Mini Program rendering. Login or simulator blockers must remain explicit; physical devices are deferred for T24. Match navigation assertions to current verified source (including later plans), not historical labels.

A polished screenshot is not sufficient. Completion requires coherent hierarchy, correct states, usable focus and touch behavior, credible content, no obscured controls, and evidence from the affected runtime. Do not update a visual baseline until the rendered change has been inspected and accepted as intentional.
