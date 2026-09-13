# Sources, licensing and adaptation

Integrated on 2026-09-12. This is a project adaptation, not an official upstream release or an endorsement. Only `wx-frontend-ui/SKILL.md` is a discoverable design skill. Supporting corpora and the search core do not add skill entry points.

## Pinned sources

- [Anthropic frontend-design](https://github.com/anthropics/skills/blob/34040c9c568585f6929bedeaad110ad08f079624/skills/frontend-design/SKILL.md), commit `34040c9c568585f6929bedeaad110ad08f079624`, source blob `a5333457c414d20d625f307df945842c0952ecc3`. [Apache 2.0 license](../licenses/Anthropic-Apache-2.0.txt).
- [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/7f69fed6a2717900085f1bc3b263721f8ba025e2/.claude/skills/ui-ux-pro-max/SKILL.md), commit `7f69fed6a2717900085f1bc3b263721f8ba025e2`, source blob `41f8e2fd7f8c568228d0b55186ebe3f7b4007377`. Copyright (c) 2024 Next Level Builder; [MIT license](../licenses/Pro-Max-MIT.txt).

Both originals and licenses were fetched at these commits during integration. Adapted instructional files are `SKILL.md`, `design-workflow.md`, `knowledge.md`, `quality-bar.md` and `verification.md`: wording is condensed and modified for this repository, not represented as verbatim upstream guidance. `scripts/search.py` is a project-authored adapter. The original BM25 core and eight full datasets are preserved under `vendor/pro-max`; [manifest.json](../vendor/pro-max/manifest.json) records paths and Git blob hashes. Source verification normalizes CRLF/LF for Windows checkouts.

## Traceability

| Upstream material                                                   | Integrated behavior                                                                    | Local adaptation                                                                  |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Anthropic: Ground your designs in the subject matter                | Audience, actual content, task-specific identity                                       | Pathology teaching context; no invented medical content                           |
| Anthropic: Process: plan, review against the brief, build, critique | Compact color/type/layout brief and second-pass anti-template review before coding     | Response-level brief, no mandatory new UpdatePlan for maintenance                 |
| Anthropic: Design principles; Restraint and self-critique           | Meaningful structure, deliberate typography, one focal point, screenshot critique      | Chinese font roles, native titles, restrained motion; no automatic hero           |
| Anthropic: More on writing in design                                | Task language, consistent action/outcome vocabulary, useful empty/error states         | Preserve actual contracts and Chinese UX copy                                     |
| Pro Max: Query Contract; Detailed Searches; Stack Guidelines        | Explicit domains, outcome-first search, verify fit, one retry, honest no-match         | Offline original BM25 and scoped corpora, Vue only; examples filtered for uni-app |
| Pro Max: Generate Design System; Master + Overrides                 | Synthesize product/style/color/type decisions; shared rules plus scoped exceptions     | Existing design document remains authoritative; no parallel generated master      |
| Pro Max: Design Dials                                               | Variance, motion and density as independent design choices                             | Reasoned decisions, not numeric aesthetic grading or forced GSAP                  |
| Pro Max: Rule Categories by Priority                                | Accessibility/touch first, then performance/layout/style/type/feedback/navigation/data | Project quality bar and evidence matrix; no global 0ms-transition ban             |

## Deliberately not imported

No second UI entry point, upstream installer, plugin settings, marketing/slides/brand subskills, unrelated stack datasets, or runtime packages. The automatic design-system renderer and persistence scripts are excluded because their generic card CSS, landing-page composition and default transitions conflict with this project's task-first layout. Knowledge retrieval and the design-system decision method are retained; the wrapper does not advertise unsupported generator flags.

When upgrading, review the pinned source diff, dataset/platform changes and licenses, update the manifest with actual upstream hashes, rerun source verification and representative retrievals, and inspect output relevance. Do not silently track `main` or copy new rules into every reference. Static checks prove provenance/structure, not visual quality of future pages.
