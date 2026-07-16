# 0033 Bounded V1 Correctness Recovery

## Outcome

The v0.1.0 data and deterministic evidence have been rebuilt from a corrected
CARA importer and passed a second pre-run semantics audit. The historical
paper-50 numerical results are retired; they are not inputs to the new
manuscript.

## Correctness changes

- Official CARA split integers are resolved positionally with `.iloc`.
- Every resolved row is checked against the task key encoded by the split.
- Out-of-range positions, task mismatches, duplicate candidate identities, and
  support/candidate identity overlap fail the build.
- Target and assay-endpoint fields are retained in each card's assay context.
- The source `pChEMBL Value` is labeled `pChEMBL`, its higher-is-better
  direction is explicit in cards and prompts, and no endpoint is mislabeled as
  pIC50.
- Build manifests and audits are deterministic and omit wall-clock timestamps.
- Public system input and scorer-only outcomes are separate, versioned,
  hash-bound artifacts.
- Non-oracle execution receives only the allowlisted public projection.

## Frozen v0.1.0 artifact

- Benchmark version: `0.1.0`
- Data version: `cara-lo-all/0.1.0`
- Official `LO_All` tasks considered: 100
- Included cards: 91
- Excluded cards: 9, all for fewer than ten feasible candidates
- Support compounds per card: 50
- Candidate-pool range: 52--967
- Feasible-pool range: 12--579
- Public input SHA256:
  `c18e66c726bb26f8afc3ba8422b21ec327444560d92750421f0dc44a2f393d9e`
- Scorer outcomes SHA256:
  `96b5d6060e3c75dda34d835fd166fd074ca5621c18924aa0ea2714acba173ff4`

Two final builds from independently re-imported records produced byte-identical
normalized records, public input, scorer outcome, metadata, and audit artifacts.

## Deterministic evidence

All 91 cards were run through oracle, random-valid, rules-only, similarity, and
three QSAR baselines. The corrected hierarchy is nontrivial: rules-only
`66.9215`, random-valid `68.4688`, similarity `73.2882`, QSAR SVM `74.9664`, and
oracle `79.5626` feasible utility. All selections had whole-action validity and
valid-selection fraction `1.0`, so this run isolates ranking utility rather than
format failures. Per-system traces, scores, and comparison artifacts were
byte-identical in an independent rerun.

## Minimum LLM experiment

The release plan freezes 546 exact requests: 91 cards times two interfaces
(`bare_llm`, `llm_tools`) times three current model conditions. The OpenAI
condition uses the dated `gpt-5.5-2026-04-23` snapshot; Anthropic uses Claude
Opus 4.8; DeepSeek is date-qualified in the condition ID and must preserve the
provider-returned model name in each trace.

At pricing checked on 2026-07-16, the conservative estimate is `$106.0594` for
546 currently uncached calls, with a maximum estimated input of `158274` tokens.
No live provider calls were made. The fixed preflight is task
`CARA_LO_CHEMBL1006579_IC50_0001` across two interfaces and three models: six
requests, maximum conservative input `25817` tokens, and a `$0.936717455`
upper-bound estimate. It uses the full matrix cache with pilot gates `$1`, six
calls, and 30000 tokens. Only after all six cache entries are present may the
residual matrix use gates `$119`, 540 calls, and 175000 tokens, preserving the
aggregate `$120` ceiling.

The exact request export SHA256 is
`50e518893b19d4a7efd64c62e08ab94d610815f8fb7518c9af4b64ff40b6f6c5`;
the pre-run cost estimate SHA256 is
`d11ce35da68e5082153be4bc57c027915ccb76cf8fb19b02e5adf767b2ab525d`.
Both files were regenerated independently and were byte-identical.

## Offline release preflight

The manuscript and supplement compile to six and two pages respectively and
were visually checked after the corrected activity and action-validity wording.
The v0.1.0 wheel and source distribution were built and the wheel was installed
in an isolated Python 3.12 environment; CLI help, system listing, and fixture
validation passed. Distribution SHA256 values are
`33e348ebdbbcbc610fe22df9322c8bc4566c173a56cda5e815ea1f3d0329881d`
and `8d1c8580d3ae0a72b0ffe57f6480be28889e8689361f51e35ed46046e48ba2d8`.

## Release consequence

The project is now framed as an action-level unit test for evidence-to-assay
batch decisions in future automated laboratories. CARA remains the credited
activity-data and split substrate. SpecGuard-Chem's contribution is the bounded
action contract, label-separation boundary, systems evaluation, and
reproducibility package—not a claim to be a new biological dataset or a complete
drug-discovery benchmark.
