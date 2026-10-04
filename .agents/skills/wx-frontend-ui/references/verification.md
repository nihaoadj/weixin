# Frontend Verification

Use [development](../../../../docs/development.md) for commands and scoped format, lint, type, behavior and boundary checks. Pure document/skill maintenance needs no application build or Demo walkthrough.

For every affected Demo-visible runtime change, synchronize its interface contract and key states, then follow [WeChat validation](../../../../docs/wechat.md) through the minimal role/entry/flow. That document is the single source for the explicit Demo watcher, development directory, ordinary compile, current CLI, real element actions, internal screenshots and stopping conditions. Do not invoke desktop capture for Mini Program acceptance.

Build, DOM tests and SDK connection do not prove rendering. Inspect affected controls, text, scrolling, fixed bars, safe areas and reachable long/empty/error states. Capture only changed or otherwise required visual states; record missing environments or evidence as unverified.

For substantial redesigns, compare the rendered result with the brief on these applicable dimensions:

| Dimension           | Evidence                                                                          |
| ------------------- | --------------------------------------------------------------------------------- |
| Hierarchy           | Clear page/module/record/field grouping, source identity and primary action       |
| Type and layout     | Legible Chinese/long content, purposeful spacing, representative widths           |
| Controls and states | Predictable labels/outcomes, pending/empty/error behavior, no obscured actions    |
| Accessibility       | Observed contrast, touch targets, labeling and applicable focus/keyboard behavior |

Record commands, exit codes, runtime/width, inspected evidence and gaps. Fix observed failures within scope; repeat only the checks invalidated by a change. Screenshot stability alone is not quality or current acceptance.
