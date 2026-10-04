---
name: wx-frontend-ui
description: Design, implement or audit WeChat Mini Program pages and components in this Vue/uni-app repository.
---

# WX Frontend UI

Use the existing Vue/TypeScript/uni-app stack. Read only guidance relevant to the affected page/state:

- Layout, controls and accessibility: [UI](../../../docs/ui.md); inspect shared tokens and inherited selectors before editing.
- New pages/substantial redesign: [design workflow](references/design-workflow.md); state a compact direction before implementation. Narrow fixes need only affected-state decisions.
- Local design/UX retrieval: [knowledge](references/knowledge.md) when needed, with [pinned sources](references/sources.md). Routine fixes need no search.
- Business reads/writes or navigation: the relevant [architecture](../../../docs/architecture.md#前端模块与公开接口) and [product](../../../docs/product.md) sections.
- Checks and rendered evidence: [verification](references/verification.md). Pure document/skill maintenance needs no build.

Implement through the affected Demo flow and inspected Developer Tools rendering, resolving observed defects within scope. Apply [quality-bar](references/quality-bar.md) for substantial redesign critique. Report missing runtime evidence; build/DOM results do not prove rendering.

For audit-only requests, report evidence-backed defects, locations and impact; distinguish preferences and unverified behavior. Make fixes when requested.
