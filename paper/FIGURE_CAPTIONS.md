# Figure Captions

This file tracks manuscript figure captions while figures are being drafted.
See `paper/FIGURE_STORYBOARDS.md` for editable ASCII/Mermaid figure drafts.

## Figure 1

**Example frozen decision card.** The figure shows an excerpt from one
CARA-derived lead-optimisation decision card. Each card contains task metadata,
a support set with visible activity values and molecular descriptors, a
candidate pool with molecular descriptors, hard output and molecular
constraints, a fixed selection budget, and an output schema for ranked
candidate identifiers. Candidate activity values are retained in the frozen
artifact for offline scoring but are hidden from evaluated deployable systems;
only the oracle upper-bound control uses them directly.

## Figure 2

**Benchmark pipeline and evaluation flow.** Public CARA/ChEMBL
lead-optimisation records were converted into 50 fixed decision cards. Each
method received the same card and returned a ranked top-10 shortlist of
candidate compounds. Shortlists were assessed in two ways: compliance, meaning
whether the shortlist followed the task rules, and hidden-activity score,
meaning whether the selected compounds had high withheld activity values. The
oracle is shown separately as an upper bound because it can see the hidden
activity values; language-model results are reported before and after
validation/repair.

## Figure 3

**Main system comparison.** Dots show mean feasible utility across the 50
decision cards; horizontal bars show 95% bootstrap intervals over cards. The
oracle is a non-deployable upper bound because it uses hidden candidate
activity. The plot includes selected language-model variants with and without
extra molecular descriptors. The strongest deployable comparator was QSAR
linear SVR, while the strongest guarded language-model row was OpenAI gpt-5.5
with validation/repair.

## Figure 4

**Ranking quality by system.** Dots show mean NDCG@10 across the 50 decision
cards; horizontal bars show 95% bootstrap intervals over cards. NDCG@10
measures whether compounds with higher hidden activity values were placed
nearer the top of the ranked shortlist. The plot includes selected
language-model variants with and without extra molecular descriptors. This
complements feasible utility, which mainly measures the quality of the selected
top-10 set.

## Figure 5

**Raw versus final utility for selected language models.** The figure shows
selected conditions for each frontier language model, including versions with
and without extra molecular descriptors. Raw output means the language-model
response before deterministic repair. Final output means the guarded pipeline
after validation and repair. "Repair used" is the percentage of the 50 tasks
where repair was applied before final scoring.

## Figure 6

**Raw versus final compliance for selected language models.** Compliance is
the fraction of the requested top-10 shortlist that satisfied the task rules.
Final compliance reaches 1.000 because the validator/repair layer enforces the
output contract. The figure includes selected conditions with and without extra
molecular descriptors. The raw compliance values show how often the
model/interface already followed the rules; "repair used" is the percentage of
the 50 tasks where repair was applied before final scoring.

## Figure 7

**Leaderboard snapshot.** Compact summary of leading rows for feasible utility,
NDCG@10 ranking quality, and raw language-model compliance. The compliance
panel uses raw language-model outputs because final guarded compliance is
enforced by validation/repair and is therefore not a useful leaderboard.

## Figure 8

**Raw language-model failure taxonomy.** Counts of raw language-model tasks
with no detected issue, molecular-rule failures, shortlist-format failures, or
JSON/schema failures before validation/repair. Categories can overlap on the
same task, so counts should not be summed across a row.
