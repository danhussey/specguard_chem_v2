---
theme: default
title: Guarded LLMs for Constrained Compound Prioritisation
info: Simple accessible SpecGuard-Chem research presentation
class: text-left
transition: none
drawings:
  persist: false
mdc: true
---

<div class="kicker">SpecGuard-Chem v2</div>

# Guarded LLMs for constrained compound prioritisation

<p class="subtitle">
Evaluating language-model systems on CARA-derived lead-optimisation decision cards.
</p>

<div class="fact-row">
  <div><strong>50</strong><span>frozen cards</span></div>
  <div><strong>10</strong><span>selections per card</span></div>
  <div><strong>2</strong><span>reported axes: utility and compliance</span></div>
</div>

---

# The practical problem

- Lead optimisation often means choosing which existing compounds to test next.
- This is not de novo molecule generation.
- It is a constrained top-k selection task:
  - choose from a fixed candidate pool;
  - return exactly `k = 10` candidate IDs;
  - avoid duplicates, support compounds, and out-of-pool IDs;
  - respect simple molecular constraints.

<p class="takeaway">
The benchmark asks whether systems return useful and valid next-test priorities.
</p>

---

# Decision card structure

<div class="steps" aria-label="Decision-card pipeline">
  <div><span>1</span><p>CARA / ChEMBL-derived task</p></div>
  <div><span>2</span><p>Visible support compounds and support activity</p></div>
  <div><span>3</span><p>Visible candidate pool with hidden candidate activity</p></div>
  <div><span>4</span><p>Systems return ranked candidate IDs</p></div>
  <div><span>5</span><p>Scorer computes utility and compliance</p></div>
</div>

<p class="note">
Candidate activity is hidden from evaluated systems and used only for retrospective scoring.
</p>

---

# Dataset snapshot

| Quantity | Value |
| --- | ---: |
| Decision cards | `50` |
| Selection budget | `10` |
| Mean support compounds | `48.76` |
| Mean candidate pool | `292.16` |
| Candidate pool range | `134-967` |
| Mean feasible candidates | `162.4` |
| Feasible candidate range | `45-618` |

<p class="note">
Dataset contribution: not new assay data; a frozen decision-card benchmark and scoring harness.
</p>

---

# Systems compared

| Family | What it does |
| --- | --- |
| Oracle | Non-deployable upper bound using hidden candidate activity |
| Random valid | Random feasible candidates |
| Rules-only | Feasible candidates ranked by descriptor desirability |
| Similarity | Feasible candidates nearest to best active support compound |
| QSAR | Per-card models trained on support fingerprints and support activity |
| LLMs | Direct-JSON prompt/interface conditions, with optional validator repair |

<p class="note">
QSAR is the key deployable conventional comparator. The oracle is only a ceiling.
</p>

---

# Metrics

<div class="two-column">
  <div>
    <h2>Usefulness</h2>
    <ul>
      <li><strong>Feasible utility</strong>: hidden activity summed for valid selected candidates.</li>
      <li><strong>NDCG@10</strong>: ranking quality with higher weight near the top.</li>
      <li><strong>Constrained regret</strong>: oracle utility minus system utility.</li>
    </ul>
  </div>
  <div>
    <h2>Validity</h2>
    <ul>
      <li><strong>Compliance</strong>: valid selected entries divided by `k`.</li>
      <li><strong>Raw metrics</strong>: before deterministic repair.</li>
      <li><strong>Final metrics</strong>: after validator repair.</li>
    </ul>
  </div>
</div>

<p class="takeaway">
Compliance and utility are reported separately because neither is sufficient alone.
</p>

---

# Headline leaderboard

| System | Feasible utility | NDCG@10 | Compliance |
| --- | ---: | ---: | ---: |
| Oracle upper bound | `89.022` | `1.000` | `1.000` |
| QSAR linear SVR | `81.382` | `0.910` | `1.000` |
| QSAR gradient boosting | `80.888` | `0.900` | `1.000` |
| QSAR random forest | `80.634` | `0.901` | `1.000` |
| Best final LLM | `78.188` | `0.881` | `1.000` |
| Similarity baseline | `73.603` | `0.825` | `1.000` |
| Rules-only baseline | `66.043` | `0.764` | `1.000` |

---

# Main comparison

<div class="result">
  <strong>QSAR linear SVR beat the best final LLM by `+3.194` feasible-utility points.</strong>
  <span>95% paired bootstrap interval: `1.942` to `4.692`.</span>
</div>

<ul>
  <li>The best final LLM was OpenAI direct-JSON plus validator.</li>
  <li>It remained below the strongest QSAR comparator.</li>
  <li>It still beat the strongest simple non-QSAR baseline.</li>
</ul>

<p class="takeaway">
The balanced result: guarded LLM systems were useful, but not best-in-class here.
</p>

---

# Raw versus final LLM outputs

| System row | Raw utility | Final utility | Raw compliance | Final compliance | Repair rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI validator | `76.758` | `78.188` | `0.976` | `1.000` | `0.140` |
| OpenAI tools + validator | `77.209` | `77.688` | `0.994` | `1.000` | `0.040` |
| Anthropic validator | `55.388` | `74.274` | `0.710` | `1.000` | `0.720` |
| DeepSeek validator | `49.201` | `67.621` | `0.726` | `1.000` | `0.560` |

<p class="note">
Final guarded-system scores should not be described as raw model ability.
</p>

---

# Failure modes

- Original high-reasoning/full-pool settings had structural interface failures.
  - Some rows had schema failure on `50/50` cards.
  - This is an interface/output-budget failure, not a clean chemistry-reasoning result.

- Direct-JSON reduced visible parse failures but did not guarantee task-valid selections.
  - We did not use strict schema-enforced Structured Outputs.
  - Deterministic validation still checked exact `k`, pool membership, duplicates, support exclusion, and molecular limits.

- Common failure categories:
  - wrong number of selections;
  - out-of-pool IDs;
  - support-set selections;
  - hard-constraint violations.

---

# Important design caveats

- `bare_llm` was a minimal JSON-interface baseline.
  - The hard constraints were present in the JSON payload.
  - The prompt did not strongly foreground constraint-following.

- `llm_tools` is better described as a descriptor-summary prompt.
  - It added TPSA, HBD, HBA, and rotatable bonds.
  - It also changed the prompt wording.
  - This is a confounded interface ablation, not a clean descriptor-only effect.

- The simplified constraints are not ADMET, toxicity, synthesis feasibility, or selectivity.

---

# What the dataset contributes

- Converts CARA lead-optimisation tasks into constrained decision cards.
- Freezes support compounds, candidate pools, constraints, and budgets.
- Hides candidate activity from evaluated systems.
- Scores both usefulness and validity.
- Preserves raw and final LLM outputs separately.

<p class="takeaway">
The contribution is the decision framing and auditability, not new wet-lab assay data.
</p>

---

# Take-home messages

1. Strong conventional baselines matter.
2. Utility and compliance answer different questions.
3. Validator repair can improve final outputs while changing the evaluated object.
4. Guarded LLMs were useful on this benchmark.
5. QSAR remained the strongest deployable comparator in the paper-50 result set.

<p class="closing">
Best conclusion: careful system evaluation, not hype or dismissal.
</p>
