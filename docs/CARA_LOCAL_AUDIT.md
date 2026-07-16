# CARA Local Audit

Release candidate: SpecGuard-Chem v0.1.0 (unreleased)

Audit date: 2026-07-16

> **Validity notice.** Counts and results from the former paper-50 build are
> invalid because that importer treated CARA split positions as data-frame
> labels. They are retained only in historical plans and the run ledger. This
> document describes the corrected v0.1.0 artifacts.

## Upstream Source

- Dataset: CARA v1.0.1
- DOI: `10.5281/zenodo.14740896`
- License: CC BY 4.0
- Source: `https://zenodo.org/records/14740896/files/CARA.zip?download=1`
- Archive bytes: `103511135`
- Archive SHA256:
  `87a71c2040d1a1434348d35691242ab1327b846cf06a46f1d64cd060867de12c`
- Local archive: `data/raw/cara/CARA.zip` (ignored by Git)

The release records the source details in
`data/releases/v0.1.0/source_provenance.json`. Relevant members are:

| Member | Size/count | SHA256 |
| --- | ---: | --- |
| `CARA/Task/LO_All.tsv` | 1,187,136 data rows; 185,008,770 bytes | `d83f9936c907635143d047af547db1f2b332375e4f930082b75c9c61a81ddf6a` |
| `CARA/Split/LO_All_support.json` | 100 task keys | `273c01297977bf82b9c983ad7616cb3e5f3ca318df6c75a040204611ef742f8a` |
| `CARA/Split/LO_All_query.json` | 100 task keys | `5c2c7c0908dd87d3a5d2fc5139dd6a1283affb1b2050d4ac8360228a859993bd` |

## Correct Split Semantics

The support/query JSON values are zero-based row positions in
`Task/LO_All.tsv`. The corrected importer:

1. resolves every reference positionally;
2. rejects out-of-range positions;
3. requires the resolved source row's `Task ID` to equal the split key;
4. rejects duplicate compound identities within a role and support/candidate
   identity overlap within a task; and
5. preserves target and endpoint context for task-coherence checks.

The import resolves all 24,588 official split references: 5,000 support records
and 19,588 candidate records across 100 tasks, with exactly 50 support records
per task. The audit found zero task-key mismatches, out-of-range positions,
silently dropped rows, mixed-target tasks, mixed-endpoint tasks, duplicate
within-role identities, or support/candidate identity overlaps.

## Reconstruct the v0.1.0 Artifacts

```bash
uv run sgchem import-cara data/raw/cara \
  --split-name LO_All \
  --out data/interim/cara_lo_all_records.jsonl

uv run sgchem build-cards data/interim/cara_lo_all_records.jsonl \
  --out data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes-out data/releases/v0.1.0/scorer_outcomes.jsonl \
  --benchmark-version 0.1.0 \
  --data-version cara-lo-all/0.1.0 \
  --target-cards 100 \
  --budget-k 10 \
  --support-size 50 \
  --selection-policy first \
  --constraints configs/default_constraints.json

uv run sgchem validate-cards \
  data/releases/v0.1.0/system_input_cards.jsonl \
  --scorer-outcomes data/releases/v0.1.0/scorer_outcomes.jsonl
```

The normalized interim records are rebuild inputs, not part of the release
bundle. Their SHA256 is
`cec651b6e97f044bf82820c465b441763cafa18a34b12361a33e79ab30faf438`.

## Frozen Build

The builder considers all 100 tasks under the explicit v0.1.0 constraints. A
task is included only if it has at least `k=10` feasible candidates. The final
artifact contains:

- 91 decision cards, each with 50 support examples and budget `k=10`;
- candidate pools from 52 to 967 compounds (mean 200.055);
- feasible pools from 12 to 579 compounds (mean 110.165); and
- nine exclusions, all recorded as `insufficient_feasible_candidates` in
  `system_input_cards.audit.json`.

Two independent final builds produced byte-identical system inputs, scorer outcomes,
build metadata, and inclusion audit.

| Release artifact | SHA256 |
| --- | --- |
| `system_input_cards.jsonl` | `c18e66c726bb26f8afc3ba8422b21ec327444560d92750421f0dc44a2f393d9e` |
| `scorer_outcomes.jsonl` | `96b5d6060e3c75dda34d835fd166fd074ca5621c18924aa0ea2714acba173ff4` |
| `system_input_cards.meta.json` | `d986ba96589032c59dac2dcc24cadf9aa3325616fa2a395cec682ece7220af54` |
| `system_input_cards.audit.json` | `abb80ad110ef71d69a2cea2f09cc456399a81d431bc9e365320ab8b27064812c` |

Candidate activity labels occur only in the scorer-outcome artifact. Per-card
input hashes prevent an outcome record from being silently paired with a
different public input.

## Corrected Deterministic Evidence

The complete baseline run is under
`release/v0.1.0/experiments/baselines/`. Across all 91 cards:

| System | Feasible utility | NDCG@k | Constrained regret | Action-valid | Valid-selection fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| oracle_valid_topk | 79.5626 | 1.0000 | 0.0000 | 1.000 | 1.000 |
| qsar_svm | 74.9664 | 0.9375 | 4.5963 | 1.000 | 1.000 |
| qsar_rf | 74.9580 | 0.9382 | 4.6047 | 1.000 | 1.000 |
| qsar_gbt | 74.7499 | 0.9352 | 4.8127 | 1.000 | 1.000 |
| similarity_to_best_active | 73.2882 | 0.9187 | 6.2744 | 1.000 | 1.000 |
| random_valid | 68.4688 | 0.8547 | 11.0938 | 1.000 | 1.000 |
| rules_only | 66.9215 | 0.8276 | 12.6411 | 1.000 | 1.000 |

These corrected baselines demonstrate ranking headroom after filtering. They do
not yet constitute a completed cross-model LLM comparison.
