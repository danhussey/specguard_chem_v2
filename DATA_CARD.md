# Data Card

This card documents the corrected CARA-derived SpecGuard-Chem 0.1.0 frozen
artifact, its construction, and the boundary between system-visible evidence
and scorer-only outcomes.

## Source and license

The data substrate is CARA v1.0.1, specifically the official `LO_All`
lead-optimization task table and support/query split files. CARA is distributed
under CC BY 4.0. Source URLs, byte counts, and SHA256 checksums are recorded in
`data/releases/v0.1.0/source_provenance.json`; attribution and derived-data
terms are described in `DATA_LICENSE.md` and `THIRD_PARTY_NOTICES.md`.

CARA is principally derived from ChEMBL compound-activity data and organizes
records into assay-local tasks. SpecGuard-Chem preserves CARA as the named data
substrate rather than presenting these records as a new molecular dataset.

## Data role in the benchmark

```text
CARA activity-prediction view
  support measurements + query compounds -> predict query activity

SpecGuard-Chem action view
  support measurements + candidate pool + constraints + budget
  -> issue a ranked top-k assay batch
```

The scientific label is CARA's supplied `pChEMBL Value`: a standardized
negative-log molar activity measure for which higher values indicate greater
potency. What changes is the evaluated output: a finite, actioned selection
whose opportunity cost and executability can be measured.

## Corrected positional import

CARA split JSON files map task identifiers to integer row positions in
`Task/LO_All.tsv`. The corrected importer:

1. resolves every integer with positional indexing;
2. verifies that the resolved source row's `Task ID` equals the split key;
3. fails on any out-of-range position or task mismatch;
4. preserves the official support/query role; and
5. rejects duplicate candidate identities or support/query identity overlap.

The exhaustive v0.1.0 audit resolved 24,588 of 24,588 references: 5,000 support
rows and 19,588 query rows across 100 task keys, with no task, target, endpoint,
or support/query identity mismatch.

The earlier importer used label-based lookup and invalidated the historical
paper-50 artifacts. Those outputs are not a prior version of this dataset; they
are retired erroneous results.

## Frozen artifacts

| Artifact | Visibility | Purpose |
| --- | --- | --- |
| `data/releases/v0.1.0/system_input_cards.jsonl` | Public/system-facing | Allowlisted assay context, support evidence, candidate features, constraints, budget, and provenance |
| `data/releases/v0.1.0/scorer_outcomes.jsonl` | Evaluator only during selection | Hidden candidate activity, keyed to the canonical public-card hash |
| `data/releases/v0.1.0/system_input_cards.meta.json` | Public | Build configuration, versions, counts, and artifact hashes |
| `data/releases/v0.1.0/system_input_cards.audit.json` | Public | Included tasks, explicit exclusions, and quality checks |
| `data/releases/v0.1.0/source_provenance.json` | Public | Upstream source identity, license, sizes, and checksums |
| `data/releases/v0.1.0/import_audit.json` | Public | Exhaustive split-resolution integrity evidence |

SHA256 values for the two evaluation artifacts are:

- system input: `c18e66c726bb26f8afc3ba8422b21ec327444560d92750421f0dc44a2f393d9e`
- scorer outcomes: `96b5d6060e3c75dda34d835fd166fd074ca5621c18924aa0ea2714acba173ff4`

## Visibility contract

Systems may receive:

- task, target, assay endpoint, source, and activity-scale identifiers;
- support IDs, structures, descriptors, and measured pChEMBL activity, with
  the higher-is-better direction stated explicitly;
- candidate IDs, structures, and permitted descriptors;
- hard constraints and `budget_k`; and
- benchmark/data/config provenance.

Systems must not receive:

- candidate activity outcomes;
- candidate labels embedded in free-form metadata;
- raw source paths or construction-only fields; or
- scorer artifact contents or hashes that expose outcomes.

The executable runner reconstructs a strict public projection even if a legacy
monolithic fixture is loaded. Oracle execution and scoring require the separate
outcome artifact for v0.1.0 cards. LLM request exports carry the public card hash
and provenance, not candidate outcomes.

## Card construction

Version 0.1.0 uses a prespecified deterministic build:

- split: `LO_All`;
- support size: 50;
- budget: `k = 10`;
- candidate policy: retain the full official query pool;
- task policy: include every task with at least ten feasible candidates;
- constraints: `configs/default_constraints.json`; and
- benchmark/data versions: `0.1.0` and `cara-lo-all/0.1.0`.

All 100 official task keys were considered. Ninety-one meet the feasibility
criterion. The nine exclusions and their feasible counts (`0`, `0`, `0`, `0`,
`0`, `0`, `0`, `6`, and `8`) are named in the audit artifact. No hidden outcome
was used to choose a subset among eligible tasks.

Two independent final builds produced byte-identical system input, scorer outcome,
metadata, and audit files.

## v0.1.0 composition

| Property | Value |
| --- | ---: |
| Included cards | 91 |
| Support compounds per card | 50 |
| Candidate-pool range | 52--967 |
| Mean candidate-pool size | 200.055 |
| Feasible-candidate range | 12--579 |
| Mean feasible-candidate count | 110.165 |
| Budget per card | 10 |

Each card retains CARA's target and endpoint fields as minimal biological
context. These fields support task-coherence checks and stratified analysis;
they do not make the task a multi-objective biological benchmark.

## Transform and descriptor policy

Normalized records preserve source task, target, endpoint, activity scale,
compound identity, structure, role, and source row position. The public card
states `activity_scale = pChEMBL` and `activity_direction = higher_is_better`;
all support and scorer outcome records use `activity_type = pChEMBL`.
RDKit-derived descriptors and constraint outcomes are deterministic under the
locked software environment.
Canonical ordering and hash serialization are defined in the artifact code.

Build configuration SHA256:
`425a40d3b64ac8398c49dfc04508e1c66522754c4e07e75e69810bc2517d9a6a`.

Normalized-record source SHA256:
`cec651b6e97f044bf82820c465b441763cafa18a34b12361a33e79ab30faf438`.

## Appropriate use

- Retrospective comparison of candidate-selection systems on identical cards.
- Analysis of ranking utility, regret, action validity, repair, and operational
  cost.
- Reproducible development and testing of constrained scientific agents.

## Inappropriate use and limitations

- Do not interpret selected compounds as prospective biological, safety, or
  clinical recommendations.
- Do not infer synthesis feasibility, selectivity, ADMET, or toxicity from the
  current constraints.
- Do not train on or otherwise expose scorer outcomes during selection.
- Do not merge results across card versions without explicit version labels.
- Do not claim that retrospective potency alone represents full drug-project
  value.
- CARA/ChEMBL measurement and curation heterogeneity remains present.
- The one-shot assay-local task omits sequential learning and cross-assay
  portfolio trade-offs.

## Rebuilding and validation

Exact commands, source locations, and run evidence are recorded in
`plans/logs/2026-07-16-0033-bounded-v1-correctness-recovery.md` and
`docs/RUN_LEDGER.md`. The release bundle will include machine-readable manifests
and checksums so a reviewer can validate the frozen artifacts without access to
candidate outcomes during system execution.
