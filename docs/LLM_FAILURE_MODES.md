# LLM Failure Modes

This note records the observed LLM-interface failure modes from the paper-50
runs. It is part of the methods record: these are not chemistry conclusions by
themselves, but they explain why raw and repaired outputs must be separated.

## Validator Terminology

In this repository, a `*_validator` system is not just a passive validator. It is
a guarded system with two deterministic stages:

1. Check the raw model output against the task contract: schema, candidate-pool
   membership, duplicates, support-set exclusion, and hard constraints such as
   RDKit-computed property bounds or alert rules.
2. If the raw output is invalid, repair it by keeping valid selections and
   filling missing slots with the deterministic fallback ranking.

The checker is not an oracle. It does not see hidden activity values and cannot
know the best compounds. The repair fallback is harness behavior, not model
behavior. For paper claims, report:

- raw LLM metrics from `raw_output` and `raw_issues`;
- final guarded-system metrics from `output` and `issues`;
- `repaired_rate` and `repaired_from_empty_rate`.

The repair fallback is useful as an operational guardrail condition, but it must
not be described as raw LLM medicinal-chemistry performance.

## Original High-Reasoning Failure Mode

```mermaid
flowchart TD
    A["Decision card"] --> B["Full-pool prompt"]
    B --> B1["Support set with activities"]
    B --> B2["Candidate IDs, SMILES, descriptors"]
    B --> B3["Hard constraints"]
    B --> B4["JSON output contract"]

    B --> C["High-reasoning / thinking model call"]
    C --> D1["Good path: visible JSON"]
    C --> D2["Failure: reasoning-token sink"]
    C --> D3["Failure: malformed or partial answer"]
    C --> D4["Failure: provider quota, credit, overload, timeout"]

    D1 --> E1["Raw selections can be scored"]
    D2 --> E2["Visible response is empty or {}"]
    D3 --> E3["Wrong k, duplicate IDs, bad IDs, prose, invalid JSON"]
    D4 --> E4["No complete trace for that condition"]

    E2 --> F2["Raw utility = 0 or schema failure"]
    E3 --> F3["Raw compliance/utility degraded"]
    F2 --> G["Validator-repair condition may fill missing IDs"]
    F3 --> G
    G --> H["Final guarded score can look valid"]
```

The key observed OpenAI high-reasoning failure was not that the model selected
bad compounds; it often failed to produce visible final JSON at all. The output
budget was consumed by reasoning tokens, leaving no usable candidate list.

## Why Repair Can Mislead

```mermaid
flowchart LR
    A["Raw model response"] --> B["Contract checker"]
    B --> C["Raw score"]
    B --> D["Repair fallback, only for *_validator systems"]
    D --> E["Final guarded-system score"]

    C --> F["Measures model behavior"]
    E --> G["Measures model + deterministic harness behavior"]
```

A repaired final score answers an operational question: "Can this guarded system
produce a valid list?" It does not answer the model-quality question by itself:
"Did the model choose useful valid compounds unaided?"

## Current Direct-JSON Mitigation

The direct-JSON interface keeps the same cards, full candidate pool, constraints,
and systems. It changes the model interface so the model is asked to emit the
final JSON object immediately, without explicit high/extended-thinking mode
where avoidable.

```mermaid
flowchart TD
    A["Same decision card"] --> B["Same full candidate-pool payload"]
    B --> C["json_first prompt profile"]
    C --> C1["Return one JSON object only"]
    C --> C2["No prose, markdown, rationale, or preamble"]
    C --> C3["No explicit thinking mode where avoidable"]

    C --> D["Model call"]
    D --> E["Raw output persisted"]
    E --> F["Contract checker"]
    F --> G["Raw metrics"]
    F --> H{"Validator system?"}
    H -->|No| I["Final output = raw output"]
    H -->|Yes, raw invalid| J["Deterministic repair fallback"]
    H -->|Yes, raw valid| I
    J --> K["Final guarded metrics"]
    I --> K
```

This mitigation does not change the benchmark task. It is an interface ablation:
direct final-answer JSON versus high-reasoning/thinking interface.

## Cost And Feasibility Failure

The full-pool prompt is itself large. A single tool-summary decision card can
contain more than 100k prompt tokens depending on provider tokenization. Provider
quota failures therefore need to be treated as run-feasibility failures, not as
model-performance scores.

Before future live runs, use cheap pilots and explicit budget gates. A full run
should not start unless estimated calls, tokens, and cost are acceptable.
