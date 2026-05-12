# SpecGuard-Chem v2 Supervisor Pack

Meeting date: 13 May 2026

Purpose: re-orient the project after SpecGuard-Chem v1 and agree the next
paper-facing direction.

## 1. The 30-Second Version

SpecGuard-Chem v2 is no longer framed as a broad LLM drug-design benchmark. It
is now a focused audit of a narrower question:

> When a medicinal-chemistry decision system follows the written rules, does it
> also make useful compound-prioritisation decisions?

The project evaluates systems that must choose the next `k` compounds to test
from a fixed candidate pool. The selected compounds must obey hard constraints
and should have high hidden activity. This lets us measure both compliance and
utility instead of confusing one for the other.

## 2. What Changed Since v1

| v1-style risk | v2 framing |
| --- | --- |
| Looks like a generic LLM compliance benchmark. | Framed as compliance-versus-utility audit. |
| Could be mistaken for de novo drug generation. | Only ranks provided candidate IDs. |
| Could compete with CARA or MolClaw. | Uses CARA-like data as substrate, not as a replacement benchmark. |
| Formatting/validity could become the whole story. | Reports raw utility, compliance, repair, and regret separately. |
| LLMs might be compared only with LLMs. | Compares against random, rules, similarity, QSAR, and oracle controls. |

## 3. Real-World Drug-Development Context

The current run focuses on lead optimisation (LO). In a real medicinal-chemistry
project, this is the stage where some compounds have already been tested and
the team must decide what to assay next.

This matters because a recommendation can fail in two different ways:

- It can be active but invalid for the project spec, such as violating property
  limits or recommending an already-tested compound.
- It can be perfectly valid but low-value, such as choosing weak candidates that
  are unlikely to move the project forward.

The project asks how to evaluate systems on both axes at once.

## 4. Current Experimental Setup

```text
CARA lead-optimisation assay tasks
        |
        v
Decision cards
support compounds + candidate pool + constraints + budget k
        |
        v
Systems under test
rules, similarity, QSAR, LLMs, LLM+validator, LLM+tools
        |
        v
Raw audit and deterministic validation
schema, candidate IDs, duplicates, support exclusion, RDKit/property checks
        |
        v
Hidden scoring
feasible utility, NDCG@k, compliance, regret, repair rates
```

Current completed data:

- 50 frozen CARA LO decision cards.
- `k = 10` compounds selected per card.
- 50 already-tested support compounds per card.
- Mean candidate pool size: about 292 compounds.
- Mean feasible candidate count after constraints: about 162 compounds.

## 5. Systems Compared

| Family | What it means here |
| --- | --- |
| Oracle | Non-deployable upper bound using hidden activity values. Sanity check only. |
| Random valid | Randomly chooses feasible candidates. |
| Rules-only | Applies constraints, then ranks by simple property desirability. |
| Similarity | Ranks candidates by similarity to the best active support compound. |
| QSAR | Trains a conventional ML model per card on support compounds, then predicts candidate activity. |
| Bare LLM | LLM receives the decision card and returns candidate IDs. |
| LLM + validator | LLM output is checked and repaired deterministically where possible. |
| LLM + tools | LLM sees computed descriptor/tool-summary fields. |
| LLM + tools + validator | Tool-summary LLM condition plus deterministic validation/repair. |

Important distinction: validator-assisted final scores are guarded-system
behavior. Raw metrics are closer to raw model behavior.

## 6. Headline Result

| System | Feasible utility | NDCG@k | Compliance |
| --- | ---: | ---: | ---: |
| Oracle upper-bound | 89.022 | 1.000 | 1.000 |
| QSAR linear SVR | 81.382 | 0.910 | 1.000 |
| QSAR gradient boosting | 80.888 | 0.900 | 1.000 |
| QSAR random forest | 80.634 | 0.901 | 1.000 |
| Best final LLM: OpenAI gpt-5.5 low reasoning Direct JSON + validator | 78.188 | 0.881 | 1.000 |
| Best raw LLM: OpenAI gpt-5.5 low reasoning Direct JSON + tools/validator instrumentation | 77.209 | 0.866 | 0.994 |
| Similarity-to-best-active baseline | 73.603 | 0.825 | 1.000 |
| Rules-only baseline | 66.043 | 0.731 | 1.000 |

Short interpretation:

- QSAR is currently the strongest deployable system family.
- The best LLM rows are useful and beat simple rules/similarity in some cases,
  but they do not beat QSAR in this run.
- Compliance can be made very high without guaranteeing high utility.
- Raw-versus-final reporting matters because validator repair can change scores.

## 7. What The Result Supports

- H1: validators improve compliance more reliably than raw model utility.
- H2: QSAR and similarity baselines are competitive and must stay in the paper.
- H3: hybrid LLM systems look more plausible than naked LLMs, but this is not
  yet the broader agent design where QSAR, RDKit, retrieval, and similarity are
  active callable tools.
- H4: compliance and utility are imperfectly correlated.

Main paper claim:

> SpecGuard-Chem contributes a decision-audit protocol that separates
> medicinal-chemistry utility from specification compliance and compares guarded
> LLM systems against strong non-language baselines.

## 8. What Not To Claim

- Do not claim any selected compound is a real drug candidate.
- Do not claim synthesis feasibility, ADMET, selectivity, safety, or clinical
  relevance.
- Do not claim this replaces CARA or MolClaw.
- Do not claim LLMs are intrinsically poor at medicinal chemistry.
- Do not claim compliance alone is success.
- Do not add de novo molecule generation to the first paper.

## 9. What I Want Supervisor Feedback On

1. Is the narrowed framing strong enough for the MD project?
2. Is the central claim clear: compliance is not utility, and both must be
   measured?
3. Are the current LO paper-50 results enough to write an initial results and
   discussion section?
4. Should the next step be paper writing, or one tightly scoped additional
   validation run?
5. How cautious should the discussion be about LLM performance versus QSAR?

Recommended ask: approve this as an empirical audit paper, not a drug-design
agent paper.

## 10. Useful Files To Show

- `paper/RESULTS_DASHBOARD.html`: interactive dashboard.
- `paper/RESULTS_SUMMARY.md`: generated results summary.
- `paper/CARA_LO_PAPER_50_RESULTS.md`: concise result snapshot.
- `paper/tables/cara_lo_paper_50_direct_json_completed/system_comparison.csv`:
  full comparison table.
- `paper/figures/cara_lo_paper_50_direct_json_completed/compliance_utility_frontier.png`:
  static compliance-utility figure.

## 11. Glossary

- CARA: public compound-activity benchmark used as the assay/task substrate.
- LO: lead optimisation; here, choosing what to test next after some compounds
  are already measured.
- VS: virtual screening; usually broader ranking/search before a lead series is
  established. Not the current primary run.
- Support set: already-tested compounds with measured activity.
- Candidate pool: compounds available for selection.
- SAR: structure-activity relationship, the relationship between molecular
  structure and measured activity.
- QSAR: quantitative SAR; here, conventional ML models trained per card on
  support-set molecular fingerprints and activity.
- Oracle: non-deployable upper-bound scorer that uses hidden candidate activity.
- Validator: deterministic harness checks for schema, IDs, duplicates,
  support-set exclusion, and molecular constraints. It does not use hidden
  activity.
- Feasible utility: activity utility credited only for selections that satisfy
  the hard constraints.
- NDCG@k: ranking-quality metric. Higher means the best candidates are nearer
  the top of the selected list.
- Constrained regret: gap between the oracle valid top-k utility and the
  system's feasible utility.
