# Project Brief

## Title

When Compliance Is Not Utility: Auditing Guarded Agents for Constrained
Medicinal-Chemistry Compound Prioritisation

## Goal

Evaluate whether guardrails and tool-using LLM systems improve constrained
compound-prioritisation decisions, or mostly improve output validity.

## Primary Task

Given support compounds, a candidate pool, hard constraints, and a finite budget
`k`, each system returns a ranked list of `k` candidate IDs to test next.

## Non-Goals

- Do not claim biological efficacy, toxicity, synthesis feasibility, selectivity,
  or therapeutic relevance.
- Do not benchmark de novo molecule generation in v1.
- Do not compete with CARA as an activity-prediction benchmark.
- Do not compete with MolClaw/MolBench as a broad drug-discovery agent benchmark.

## Success Criteria

- Frozen decision cards can be built from CARA-like data.
- Strong non-language baselines run reproducibly.
- LLM systems run through a cache/replay adapter and optional live provider path.
- Scoring separates compliance and utility.
- Reports show the compliance-utility frontier.
