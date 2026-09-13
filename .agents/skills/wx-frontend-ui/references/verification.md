# Frontend UI Verification Routing

Project verification, strengthened on 2026-09-12 using the critique and UX-priority principles in [sources.md](sources.md). Isolated Skill/document edits require structure, links, source integrity and relevant script checks; they do not require application builds or Demo walkthroughs.

Use the smallest set that can falsify the relevant failure modes. Commands run from the repository root unless noted otherwise. The complete command source is [development.md](../../../../docs/operations/development.md).

## Static and component checks

For copy, style, component, layout, accessibility, or interaction changes:

1. Run scoped Prettier on changed frontend files.
2. Run `npm run lint` and `npm run type-check`.
3. Run the nearest Vitest component or behavior spec; run `npm test` when shared UI or navigation behavior has broad consumers.
4. Run `node scripts/frontend-boundaries.mjs` when imports, feature access, navigation infrastructure, or component ownership changes.

Do not claim visual correctness from these checks alone.

## WeChat Mini Program evidence

Treat this section as the main frontend acceptance route. Record actual visible text/controls, scrolling and overlap, not merely page data or method results. A handshake or a saved screenshot alone is not acceptance. Inspect each screenshot, retain failures, and report missing environments as unverified. T24 explicitly defers physical-device testing.

For every runtime change affecting a Demo-experienced page, component, visible copy/state, flow, data or navigation, follow AGENTS.md's independent Demo requirement, even when no UpdatePlan is needed:

1. Synchronize affected Demo seed/store/adapter behavior where needed to present the same interface contract and key states; never simulate real authorization or real AI as proof.
2. In the watcher terminal explicitly set Demo mode: PowerShell `$env:VITE_APP_MODE='demo'; npm run dev:mp-weixin`. Wait for `Build complete. Watching for changes...`.
3. Load only `D:\CODE\weixin\wxprogrom7.15\dist\dev\mp-weixin` in WeChat Developer Tools; `dist/build/mp-weixin` is not the development-tool refresh target.
4. Recompile normally in the developer tool after the watcher completes, then manually walk the affected role/entry and minimal Demo flow. Do not turn a local change into a full-suite rerun unless the release/shared-change/escalation criteria in [WeChat acceptance](../../../../docs/operations/wechat-validation.md#选择验收范围) apply. Check scroll bounds, focus/keyboard behavior, safe areas and console output. Record mode, command, directory, ordinary compile, flow, failures and the conditions to close them. Do not edit dist or clear tool data to obtain a pass.

Use the project-local `screenshot` skill only when browser tooling cannot capture the required developer-tool or operating-system evidence.

## Evidence and limits

For a visual redesign, record this compact acceptance matrix against the revised design brief. This is a project-specific rubric, not an upstream aesthetic benchmark. Mark each applicable row pass, fail or unverified with an observed reason:

| Check                     | Evidence needed                                                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Hierarchy and identity    | Main task/focal point is evident; AI reference does not overpower teacher judgment; no repeated native title           |
| Type and rhythm           | Chinese text, metadata and long answers remain readable; alignment and section spacing express grouping                |
| Composition and density   | Narrow/wide screenshots show intentional layouts; desktop width supports comparison/context; empty state has direction |
| Controls and states       | Consistent icons/buttons; real pending/error/empty states; no obscured actions or accidental horizontal overflow       |
| Accessibility and runtime | Observed contrast, touch, focus and WeChat runtime behavior rather than markup-only claims                             |

Inspect rendered output, fix failures within scope and inspect again before accepting changed baselines. Passing screenshot comparison only proves stability. An unverified item remains an explicit limitation; never call it a pass. Review-only tasks report findings without implementing fixes. Do not repeatedly rerun unchanged checks or require user approval merely for agent self-critique.

Record commands, exit codes, tested runtimes/viewports, inspected screenshots, skipped checks, and the condition needed to close each gap. Do not describe a checked-in snapshot as a current rendered inspection unless it was actually produced and reviewed in this run.
