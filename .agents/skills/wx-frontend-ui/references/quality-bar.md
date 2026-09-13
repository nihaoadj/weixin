# WX Frontend Quality Bar

Project rules, with design/UX principles adapted on 2026-09-12 from [pinned upstream sources](sources.md). Apply accessibility and touch usability first, then layout/performance, visual coherence, typography, feedback/navigation and data presentation as relevant. Upstream examples do not override product contracts.

## Product character

This is a pathology PBL teaching workspace, not a generic SaaS dashboard or consumer wellness app. The interface should feel like a well-edited clinical teaching record: calm, exact, legible under pressure, and clear about whose evidence or decision is being shown.

The visual system should communicate three relationships without ornamental explanation:

- evidence before interpretation;
- AI advice before, but subordinate to, teacher judgment;
- current action before historical context.

## Composition

- Give every page a clear reading order and one dominant next action. Use section titles that name the user's task, not the implementation module.
- Do not repeat the native navigation title as a body hero. Avoid oversized welcome panels, decorative English eyebrows, generic metric-card grids, and gradients that do not encode meaning.
- Prefer a document-like flow of headings, aligned metadata, whitespace, and light rules. Use cards for independent actions, selectable objects, or content that genuinely needs a boundary—not as the default wrapper for every section.
- Keep related evidence close enough to compare. Separate irreversible or teacher-authoritative actions from AI references and descriptive analytics.
- On desktop, use additional width to improve comparison and persistent context, not merely to enlarge mobile spacing. On small screens, preserve the same priority order and keep the primary action reachable without covering content.

## Visual system

- Inspect colors, spacing, radii, shadows, and typography in `uni.scss`, `App.vue`, and nearby shared UI components. Reuse sound values with semantic variables; inherited primitives that cause the reported problem need scoped correction, not blind preservation.
- Typography carries most of the hierarchy. Use a restrained type scale, deliberate weights, readable line lengths, and tabular alignment where numbers must be compared.
- Use color sparingly for state and priority. Pair every meaningful color with text, shape, iconography, or position; never rely on red/green alone.
- Reserve shadows and large radii for actual elevation or focus. Dense teaching records benefit more from alignment and separators than stacked floating surfaces.
- Motion should explain a state transition or preserve spatial context. Respect reduced-motion preferences and avoid ambient animation in evidence-review flows.
- Do not add remote fonts or image assets merely to make a screen appear premium. High-end quality here comes from precision, rhythm, content integrity, and restraint.

## Interaction and content

- Use realistic Chinese teaching content when adding fixtures or display examples. Test long student answers, long knowledge-point names, missing optional fields, and mixed score/status metadata.
- Use specific action labels such as “保存草稿”“反馈并发布” or “重试”. Keep the same verb in the button, pending state, success feedback, and follow-up navigation.
- Every asynchronous action needs an intentional pending state, duplicate-action protection, recoverable error, and success outcome. Preserve entered text after a recoverable failure.
- Empty states should explain why the area is empty and offer the next valid action when one exists. Do not fabricate activity, scores, diagnoses, or recommendations to fill space.
- Destructive, publishing, grading, and medically consequential actions need clear scope and consequence. AI-produced material must remain visually distinguishable from reviewed or authoritative content.

## Accessibility and cross-platform behavior

T24's product target is WeChat only, and T25 has retired the browser product path. Actual Mini Program controls, screen widths, keyboard/scroll behavior and safe areas must be observed in Developer Tools; deferred device behavior remains unverified.

- Prefer native interactive controls and visible labels. Provide meaningful names, current/selected state, focus indication and error association.
- Touch targets must remain usable on narrow screens and near safe areas. Fixed headers, footers, composers, and action bars must not obscure scrollable content or focused fields.
- Check rendered touch targets against the project's 44px minimum (48px primary submit) rather than assuming rpx gives a fixed physical size. Separate adjacent targets; upstream 8px spacing is a useful starting point, not permission to break compact native controls.
- Check normal text foreground/background contrast at 4.5:1; distinguish large-text and non-text cases when assessing accessibility. Do not assume muted gray or a database palette passes. Use readable body sizes and at least the project's 12px narrow-screen metadata floor.
- Reserve media/loading dimensions to avoid layout shifts; avoid repeated layout reads/writes and evaluate long lists before adding virtualization. Use existing icon conventions with consistent optical size/stroke and explicit action names; framework-specific icon imports are not portable assets.
- Do not assume markup-only ARIA claims reach the real input rendered by uni-app; inspect the Mini Program control instead.
- Use `100vh` for Mini Program viewports.
- Respect native page titles and navigation semantics. Verify back behavior, deep links, loading transitions, and focus after conditional content changes.
- Accessibility claims require observed keyboard, focus, labeling, contrast, and runtime evidence. Static markup review alone is not certification.

## Self-critique

Before finishing, ask:

1. Can the intended student or teacher identify the next action in a few seconds?
2. Does hierarchy express workflow and evidence, or merely decorate containers?
3. Is any information repeated, visually over-promoted, or hidden behind a card without purpose?
4. Are AI, system, student, and teacher-authored states unmistakable?
5. Does the same flow remain usable with long text, no data, failure, keyboard focus, and a narrow viewport?
6. Would removing one visual device make the interface clearer? If yes, remove it.
