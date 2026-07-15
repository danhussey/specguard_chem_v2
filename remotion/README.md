# SpecGuard-Chem v2 — Remotion explainer

Animated explanatory videos that describe the project to a general audience,
built with [Remotion](https://www.remotion.dev/) (React → MP4).

This is a self-contained sub-project. It is intentionally isolated from the
repo's Python package (`../src`) and the Slidev deck (`../package.json`), which
uses pnpm. Install and run everything from inside this `remotion/` folder.

## Install

```bash
cd remotion
pnpm install    # or: npm install
```

## Preview in the studio

```bash
pnpm studio
```

Opens the Remotion studio with a live, scrubbable timeline for every
composition.

## Render the main video

```bash
pnpm render     # -> out/specguard-chem-explainer.mp4  (1920x1080, 30fps, ~28s)
```

Render any single scene as its own clip, e.g.:

```bash
npx remotion render Scene-Leaderboard out/leaderboard.mp4
```

## Compositions

- `ProjectExplainer` — the full narrative, seven scenes in sequence.
- `Scene-Title` — title and the framing: predict vs decide.
- `Scene-PredictDecide` — the core reframing: a constrained, budget-limited
  selection decision, contrasted with property-prediction benchmarks.
- `Scene-DecisionCard` — anatomy of one frozen decision card (support set,
  candidate pool, hard constraints, budget k).
- `Scene-Coverage` — the coverage matrix (task kind × target family × endpoint);
  the live LO·All seed slice vs the roadmap. See "Data claims" below.
- `Scene-Protocol` — the baseline ladder from random to oracle and the metric
  suite, ordered by real feasible utility (QSAR above the guarded LLM).
- `Scene-Leaderboard` — animated feasible-utility results over the 50
  lead-optimisation assays; framed as a calibration point for LLM-for-chemistry.
- `Scene-Takeaway` — the closing "score the decision, not just the prediction".

## Data claims (what is measured vs aspirational)

This video is an aspirational "ideal conference incarnation" pitch. To keep it
honest:

- **Measured / live:** the leaderboard numbers (50 LO·All assays, k=10), the
  46 distinct targets across those 50 assays, 722 targets available in the CARA
  LO source, and the IC50/Ki/EC50 endpoint mix. All recoverable from
  `data/interim/cara_lo_all_records.jsonl` and the `paper/` tables.
- **Roadmap / not yet run:** every non-`LO·All` cell in the coverage matrix
  (VS task kind; Kinase / GPCR family slices). These are explicitly labelled
  "roadmap" in the scene — the source data exists, but no results are claimed.
- The baseline-ladder bar heights are illustrative (ordered by real utility) and
  carry no axis; precise numbers live only in the leaderboard scene.

## Editing

Scene components live in `src/scenes/`. Shared theme tokens are in
`src/theme.ts`; reusable animation helpers and layout primitives are in
`src/components.tsx`. Scene order and durations are defined once in
`src/ProjectExplainer.tsx`.

The leaderboard numbers mirror the paper-facing run
(`../paper/CARA_LO_PAPER_50_RESULTS.md`); update `src/scenes/LeaderboardScene.tsx`
if that result changes.
