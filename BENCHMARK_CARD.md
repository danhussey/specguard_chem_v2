# Benchmark Card

## Name

SpecGuard-Chem v2 decision-card audit harness.

## Intended Use

Offline evaluation of constrained top-k compound-prioritisation systems over
public assay-derived candidate pools. The benchmark asks whether a system can
select useful, valid candidate IDs under hard project constraints and finite
testing budgets.

## Out Of Scope

- De novo molecule generation.
- Synthesis planning.
- Clinical or therapeutic recommendation.
- Claims of biological efficacy, toxicity, selectivity, or safety beyond the
  retrospective source measurements.

## Task Shape

Each task contains support compounds with observed activity, a candidate pool
with hidden activity for scoring, hard constraints, and `budget_k`. Systems
return ranked candidate IDs only.

## Primary Metrics

- NDCG@k.
- Feasible utility.
- Constrained regret.
- Mean selected activity.
- Hit recovery and enrichment where a hit threshold is defined.
- Constraint and schema violation rates.

## Reporting Policy

Report compliance and utility separately. Validator-only gains should not be
described as medicinal-chemistry gains unless feasible utility also improves.

## Limitations

Public retrospective data do not establish prospective medicinal-chemistry
realism. CARA-derived tasks are assay-grounded but still lack wet-lab
prospective validation, synthesis constraints, ADMET evidence, and project-team
decision context.
