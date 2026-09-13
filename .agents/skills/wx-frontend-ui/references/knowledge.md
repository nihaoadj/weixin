# Pinned local design knowledge

UI/UX Pro Max's original BM25 core and eight unmodified CSV corpora are bundled under `vendor/pro-max/`. [sources.md](sources.md) records their origin. Read this reference when a design direction or specific UX question calls for retrieval; routine copy fixes do not require search.

From the repository root:

```text
python .agents/skills/wx-frontend-ui/scripts/search.py "education learning" --domain product
python .agents/skills/wx-frontend-ui/scripts/search.py "minimalism" --domain style
python .agents/skills/wx-frontend-ui/scripts/search.py "error summary validation" --domain ux
python .agents/skills/wx-frontend-ui/scripts/search.py "computed reactive" --stack vue
```

Outside the root, use the absolute path to this skill's `scripts/search.py`; data paths resolve from the script. Requires Python 3 standard library only. The wrapper is read-only, outputs JSON and supports `-n 1..20` (default 3). It exposes only bundled domains: `product`, `style`, `color`, `typography`, `ux`, `chart`, `icons`, and stack `vue`. It does not expose the upstream design-system generator, persistence or other stacks.

Preserve the upstream query contract:

1. Use one dominant intent, 2–5 meaningful English terms, and explicit domain or stack. Translate Chinese task concepts into search terms, without private content.
2. For a UX defect, query the observable outcome before framework implementation. For a new design direction, synthesize only relevant product/style/color/type results; consult chart/icons only when needed.
3. Inspect record identity, platform, applicability and the Do/Don't guidance. Ranking is lexical relevance, not proof of suitability, medical correctness, accessibility compliance, or installed-version compatibility.
4. If empty, off-topic, or redirected to an unbundled domain, retry once with a narrower supported query. If still unmatched, explicitly identify project-based reasoning as fallback. Never fabricate a retrieved record.
5. Missing/corrupt data is an error, not a successful empty match. Do not persist or apply an unverified result.

Adaptation filters:

- Product records can mix marketing conversion with application patterns. Reject social proof, pricing, invented metrics or hero content in teaching workspaces unless the task actually asks for them.
- Verified example: `education learning` retrieves `Educational App`, which recommends claymorphism and playful colors. This lexical match does not fit the adult pathology teaching workspace. Retain relevant learning-flow guidance but reject the style recommendation under the project quality bar; do not report that Pro Max prescribed our restrained clinical language.
- Typography records contain Google Fonts and Tailwind imports; retain useful role/contrast ideas, use the established Chinese stack, and verify Chinese text in the actual runtime.
- Icon records include React import examples. Reuse a consistent existing uni-app-compatible icon implementation, with correct decorative/action semantics. No emoji substitution or new package by default.
- Vue data describes upstream framework versions. Check installed versions before using APIs; Vue support does not establish WeChat/uni-app support. Browser DOM, ARIA, SVG, viewport and animation examples require platform-specific handling.
- Color swatches require actual foreground/background contrast checks. Style accessibility ratings are recommendations, not certification.

The upstream generator's master/override and design-dial ideas are retained in [design-workflow.md](design-workflow.md). Its generic card CSS, landing-page assembly, forced transitions and automatic Markdown persistence are deliberately excluded. Design synthesis is performed by the agent against this project's contracts, not claimed as a bundled generator feature.

Maintenance verification: run `python .agents/skills/wx-frontend-ui/scripts/search.py --verify-sources` and `python .agents/skills/wx-frontend-ui/scripts/test_search.py`. Tests cover every bundled domain/Vue, representative outcome relevance, different working directories, invalid options, empty matches and corrupted/missing data in a temporary copy. These are retrieval checks, not visual acceptance of the application.
