# Design, review, build, critique

Adapted on 2026-09-12 from the pinned Anthropic frontend-design and UI/UX Pro Max sources in [sources.md](sources.md). The project-specific adaptations below are not upstream claims.

## 1. Ground the direction in the actual task

Inspect the page and shared styles, available screenshots, real content lengths, audience, primary task and reachable states. Distinguish an implementation defect from a visual preference. A teacher comparing evidence needs a different composition from a student starting one task. Use known context; ask only when a missing choice would materially change the result.

For a substantial redesign, briefly state the design direction before coding. Include:

- **Identity and focus:** the user, task, and one memorable, useful visual element. A reasoning sequence or evidence/editor relationship can provide identity without a decorative hero.
- **Color:** approximately 4–6 core named values/semantic tokens and their roles; keep error, warning, and other state tokens separately. Reuse verified values where sound and explain any replacement.
- **Type:** Chinese font stack and fallback, heading/body/metadata roles, size, weight, line-height and readable measure at narrow and wide sizes. Use the project's Chinese system stack intentionally; upstream font pairings are inspiration, not a requirement to download Latin fonts. The upstream 80-character measure is not a Chinese line-length prescription.
- **Layout:** actual container widths, alignment, section spacing, control density and mobile/desktop behavior. Use small wireframes to compare materially different compositions where helpful. Assign each container a reason: continuous reading, editing, selectable object, or overlay.
- **States:** populated, empty, long content, pending and failure compositions for the affected flow. Empty is a designed state with a reason and valid next step, not a sentence stranded in a large canvas.

This brief can live in the response; it does not require a new plan document.

## 2. Use Pro Max knowledge deliberately

Follow [knowledge retrieval](knowledge.md) for targeted queries. For a new visual direction, combine product/style guidance, color/type where needed, and applicable UX/Vue results into the brief. Name the selected records and explain fit; do not merely copy the first palette or a landing-page pattern.

Use Pro Max's optional 1–10 design dials as decision aids, not quality scores:

| Dial     | Low                              | High                                  | Project adaptation                                                                               |
| -------- | -------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Variance | Familiar, restrained composition | Unconventional/asymmetric composition | Spend distinction on useful evidence relationships, not novelty navigation                       |
| Motion   | Subtle feedback                  | Complex choreography                  | Prefer low motion for teaching records; never delay feedback to satisfy an animation rule        |
| Density  | Spacious                         | More information per viewport         | Teacher comparison may be denser than student guidance; preserve readable type and touch targets |

Translate chosen dials into concrete spacing, layout and transition decisions. No score or dial guarantees beauty. Do not introduce GSAP, Tailwind, React, external fonts or icon dependencies because a retrieved example uses them.

Use the Pro Max master-plus-page-exceptions principle without creating a competing source of truth: the existing frontend design document holds shared decisions, and its page sections hold justified exceptions. For authorized lasting visual-system changes, update the relevant sections with final decisions and rationale. Never persist raw search output as accepted design, overwrite an existing decision blindly, or revive historical navigation. Local fixes need no new design-system file.

## 3. Review the brief before implementation

Apply Anthropic's second pass: would this same plan appear for an unrelated app? If so, revise the generic part and explain why. Check for identical rounded/shadow cards, decorative labels, arbitrary numbered markers, single-word headline accents, gratuitous monospace metadata, and repeated entrance animations. Numbering must express a sequence. Flat newspaper columns can be just as formulaic as cards; removing every radius does not create a design.

Treat these as contextual anti-patterns, not universal aesthetic bans. Follow the user's explicit direction. Keep one meaningful focal point and quiet supporting elements. The first viewport should foreground the task, not repeat the native page title. Wider layouts should enable comparison or persistent context rather than inflate phone-sized components.

Review against constraints and the actual CSS cascade before coding. Resolve conflicts between current shared primitives and the desired hierarchy inside the authorized scope.

## 4. Build and critique the rendered result

Implement the revised brief with the existing Vue/uni-app architecture. Preserve genuine business content, action names and outcomes. Use [quality-bar.md](quality-bar.md) for interaction and accessibility and [verification.md](verification.md) for runtime evidence.

Compare new screenshots with the brief and prior evidence at the same viewport and data state. Check focal point, reading order, typography, rhythm, density, empty-state composition and consistent controls separately from functional correctness. Fix supported problems and inspect again before accepting a baseline. If runtime inspection is unavailable, state that visual acceptance remains unverified; do not replace it with a self-assigned aesthetic score.
