# University Feedback Revision Pack

Prepared 28 July 2026 from the submitted manuscript
`md_research_project_manuscript_v0_5_with_plan.pdf`, the corrected CARA
v0.1.0 benchmark artifacts, and the completed corrected 91-card provider
matrix.

## Important evidence correction

The numerical results in manuscript v0.5 must not be edited or defended. They
were derived from the historical `cara_lo_paper_50` build, whose importer
incorrectly treated CARA split positions as dataframe labels. The 50 cards,
model responses, scores, intervals, tables, figures, and conclusions downstream
of that build are retired.

The replacement analysis:

- considers all 100 official CARA `LO_All` tasks;
- includes all 91 tasks with at least 10 candidates satisfying the declared
  constraints;
- excludes nine tasks solely because their feasible-candidate counts were
  0, 0, 0, 0, 0, 0, 0, 6, and 8;
- uses no hidden outcome to select tasks; and
- contains 91 cards × 2 interfaces × 3 provider conditions = 546 raw LLM
  requests, plus deterministic zero-call repaired views of the same responses.

This design change directly resolves the concern about selecting the 50 largest
candidate pools. It does not remove all selection limitations: inference still
applies only to eligible CARA `LO_All` tasks under the simplified constraints,
not to virtual screening, prospective medicinal chemistry, or drug discovery
generally.

The completed 91-card LLM analysis is frozen in the submission branch. Its
headline values and repair attribution have been independently recounted, and
all 546 requests have been replayed from the committed content-addressed cache
without a provider call. The final clean-checkout reproduction gate is recorded
in the execution log named under Evidence and provenance below.

## Suggested response to the university

Thank you for the detailed and constructive feedback. I have revised the report
in five main ways.

First, I expanded the literature review to distinguish chemistry-knowledge
benchmarks, molecular-property prediction, and tool-using chemistry agents. I
now position the study specifically as an action-level extension of CARA:
CARA evaluates assay-local activity prediction, whereas this study evaluates
whether those predictions can be converted into an exactly ten-compound,
constraint-compliant experimental allocation. I also define *decision card*,
*guarded*, and *feasible utility* in plain language at first use.

Second, I replaced rather than merely defended the original 50-largest-card
selection. A subsequent data-integrity audit identified an error in the
historical importer, so all numerical results from that build have been
withdrawn. The corrected benchmark considers all 100 official CARA `LO_All`
tasks and includes every task with at least ten feasible candidates, giving 91
cards. The nine exclusions are based only on the prespecified feasibility and
budget rule, not on candidate-pool size or hidden activity. I state that this
improves coverage but does not establish generalisability beyond eligible CARA
lead-optimisation tasks. I have also added the rationale for the molecular
thresholds and exact QSAR and LLM configurations.

Third, I clarified the interpretation of feasible utility. CARA supplies all
activities as pChEMBL values, a common negative-log molar scale with higher
values indicating greater potency. Nevertheless, IC50, Ki, EC50, and Potency
assays are not biologically interchangeable. The main inferential comparison is
therefore made within each card: I calculate the utility difference between two
systems on the same assay and average those paired differences across cards.
Each card receives equal weight. NDCG@10, which normalises ranking performance
against the ideal ranking within each card, is reported as a scale-robust
secondary analysis. I also describe the bootstrap sample size, seeds,
resampling unit, replacement procedure, and percentile interval calculation.

Fourth, I now separate unaided model output from model-plus-harness performance.
For the best OpenAI condition, deterministic repair was invoked on 19 of 91
cards, but fallback candidates supplied only 14 of 910 final shortlist
positions (1.54%); nine of those repairs corrected contract or rank details
without replacing a candidate identity. The dependence was much larger for
other providers: deterministic fallback supplied 25.16–58.68% of all final
positions in the Anthropic and DeepSeek conditions. These results are now
labelled explicitly as guarded pipeline results and are not attributed to the
LLM alone.

Finally, I strengthened the comparison with published work and narrowed the
claims. The corrected result is consistent with CARA's finding that
assay-specific models are strong in lead-optimisation settings and with prior
LLM studies showing substantial dependence on task, prompt, representation, and
tools. I retain explicit limitations concerning retrospective public data,
possible pre-training exposure, simplified constraints, the absence of a
medicinal-chemist comparator, and lack of prospective laboratory validation.

## Feedback-to-revision map

| Feedback | Revision | Best location |
| --- | --- | --- |
| Expand the literature | Add work on ChemLLMBench, ChemBench, LLM4SD, and ChemCrow; distinguish knowledge, prediction, and agent evaluations | Introduction and Discussion |
| Explain the addition to CARA | State that CARA supplies assay-local support/query prediction tasks; this study adds an exactly top-10 action contract, feasibility checks, whole-action validity, repair attribution, cost, and regret | End of Introduction |
| Define technical terms | Add one-sentence definitions at first use; state that *guarded* does not mean biologically safe | Abstract/Introduction and Methods |
| Justify the 50 largest pools | Do not retain this policy. Replace it with all 91 eligible tasks from all 100 official tasks | Data sources and task inclusion |
| Acknowledge generalisability | Limit inference to eligible CARA `LO_All` tasks and the tested constraints and provider snapshots | Task inclusion and Limitations |
| Justify constraints | Relate MW 500 to the conventional Rule-of-Five boundary; describe cLogP 4.5 as a prespecified simplified eligibility threshold fixed before evaluation; state what the rules omit | Task constraints |
| Make QSAR and LLM methods reproducible | Report fingerprints, hyperparameters, package versions, exact model snapshots, reasoning/thinking settings, output cap, prompt fields, calls, cache, and repair policy | Systems and Reproducibility |
| Explain utility across cards | Clarify common pChEMBL transformation, paired within-card contrasts, equal card weighting, offset cancellation for valid fixed-size lists, and the NDCG sensitivity analysis | Outcomes and statistical analysis |
| Add bootstrap detail | State 1,000 marginal or 2,000 paired resamples, seeds 7 and 13, sampling cards with replacement, and 2.5th/97.5th percentiles | Statistical analysis |
| Separate LLM from repair | Use “raw LLM” versus “LLM plus deterministic post-hoc repair” throughout | Abstract, Results, figures, Discussion |
| Report how much was replaced | Add the shortlist-position attribution table below | Results or Supplement |
| Strengthen comparison and limit claims | Compare with CARA and hybrid/tool-using LLM literature; avoid claims beyond this benchmark | Discussion and Conclusion |

## Paste-ready manuscript text

### Abstract: replacement Methods and Results wording

> **Methods:** CARA lead-optimisation data were converted into 91 assay-local
> decision cards. A decision card is one self-contained selection problem
> containing 50 previously measured support compounds, a fixed candidate pool,
> explicit eligibility rules, and a budget of ten candidates. All 100 official
> `LO_All` tasks were considered, and every task with at least ten feasible
> candidates was included. Systems comprised random, rule-based, similarity,
> per-card QSAR, raw LLM, and guarded LLM conditions. Here, *guarded* means that
> a deterministic program checks the LLM's proposed action and, if necessary,
> retains valid proposed candidates and fills missing positions using a fixed
> rule-based ranking. The primary outcome was feasible utility: the sum of the
> hidden pChEMBL activities of valid selected candidates. Systems were compared
> using paired differences across the same cards and 2,000-resample percentile
> bootstrap intervals.
>
> **Results:** Linear support-vector QSAR was the strongest deployable system
> (mean feasible utility 74.966). The strongest guarded LLM condition was the
> bare-interface GPT-5.5 snapshot plus deterministic post-hoc repair (73.964).
> The paired QSAR-minus-guarded-LLM difference was 1.003 utility points (95%
> bootstrap interval 0.405 to 1.647). Before repair, that LLM condition had
> utility 72.966 and issued a fully valid action on 72 of 91 cards. Repair was
> invoked on 19 cards, but deterministic fallback supplied only 14 of 910 final
> shortlist positions (1.54%). Repair supplied 25.16–58.68% of final positions
> in the Anthropic and DeepSeek conditions, so their guarded scores were
> substantially determined by the combined model-and-harness pipeline.

These values are generated from the corrected matrix frozen in the submission
branch.

### Introduction: expanded literature and study contribution

> Recent evaluations cover several distinct uses of LLMs in chemistry.
> ChemLLMBench evaluated five LLMs on eight chemistry tasks and found marked
> variation across tasks and in-context prompting conditions
> \cite{guo2023chemllmbench}. ChemBench evaluated chemical knowledge and
> reasoning rather than candidate prioritisation; leading models performed
> strongly overall but still failed some basic tasks and produced overconfident
> answers \cite{mirza2025chembench}. LLM4SD used an LLM to extract or infer
> interpretable chemical rules and then supplied the resulting features to
> conventional predictors such as random forests, illustrating a hybrid rather
> than an unaided-LLM approach to molecular-property prediction
> \cite{zheng2025llm4sd}. ChemCrow similarly coupled an LLM to 18
> expert-designed chemistry tools and showed the value of the complete
> tool-using system \cite{bran2024chemcrow}. Collectively, this literature
> supports evaluating LLMs as components of explicitly defined systems and
> comparing them with strong task-specific models; it does not establish that a
> raw LLM should outperform an assay-local QSAR model on compound
> prioritisation.
>
> CARA provides the assay-aware substrate for the present study. It separates
> virtual-screening from lead-optimisation assays, supplies few-shot support and
> query splits, and recommends assay-level evaluation because activity
> distributions differ among assays \cite{tian2024cara}. The present study does
> not claim a new activity dataset or a replacement for CARA. It changes the
> evaluated output from per-compound activity estimates or rankings to one
> finite action: an ordered, exactly ten-compound shortlist satisfying explicit
> eligibility and output rules. The added measurements are whole-action
> validity, shortlist utility and regret, raw-versus-repaired attribution, and
> operational cost.

### Plain-language definitions at first use

> A *decision card* is one self-contained benchmark case: it gives a system the
> compounds already tested in one assay, a finite set of candidates, the rules
> candidates must meet, and the number that may be selected.
>
> A *guarded LLM system* is the LLM plus deterministic software that checks the
> returned shortlist and repairs invalid or missing positions. In this report,
> *guarded* refers only to compliance with the stated benchmark contract; it
> does not mean that the compounds are biologically, clinically, or
> synthetically safe.
>
> *Feasible utility* is the total hidden activity of the selected compounds that
> obey the benchmark rules. An invalid selection earns zero for that position.
> It measures how well a fixed assay budget was allocated within this
> retrospective benchmark, not therapeutic or commercial value.

At later mentions, “task-local” can be replaced with “trained separately for
each assay card.”

### Data sources and task inclusion

> The corrected analysis used CARA version 1.0.1 and the official `LO_All`
> activity table and support/query splits. The split files store integer row
> positions. These were resolved positionally and checked against the task key
> on the corresponding source row. The audit resolved all 24,588 references:
> 5,000 support and 19,588 query rows across 100 tasks. Out-of-range positions,
> task mismatches, duplicated candidate identities, and overlap between support
> and candidate compounds were treated as errors.
>
> All 100 official `LO_All` tasks were considered. A task was included if at
> least ten candidates remained after the prespecified molecular-eligibility
> checks, because otherwise no system could issue the required top-10 action.
> Ninety-one tasks met this rule. The nine excluded tasks had 0, 0, 0, 0, 0, 0,
> 0, 6, and 8 feasible candidates. No task was selected according to candidate-
> pool size, model performance, or hidden candidate activity. Included
> candidate pools ranged from 52 to 967 compounds (mean 200.055), and feasible
> pools ranged from 12 to 579 (mean 110.165).
>
> This exhaustive eligibility-based policy removes the original preference for
> the 50 largest pools, but it does not make the benchmark representative of
> all lead-optimisation work. It excludes CARA tasks that cannot support the
> stated ten-compound budget, evaluates `LO_All` rather than virtual-screening
> tasks, and inherits the assay and chemical-space composition of CARA and
> ChEMBL.

### Molecular constraints and rationale

> Candidate eligibility required a structure that RDKit could parse, molecular
> weight no greater than 500 Da, and calculated logP no greater than 4.5. The
> 500-Da boundary is the conventional molecular-weight component of Lipinski's
> Rule of Five \cite{lipinski1997}. The cLogP limit of 4.5 was a prespecified
> simplified eligibility threshold fixed before model evaluation; it is 0.5
> below the conventional Rule-of-Five boundary of 5. These two thresholds were
> simple, deterministic rules with which to test contract-following; they were
> not tuned against hidden candidate activity and should not be interpreted as
> a validated medicinal-chemistry filter. The forbidden-substructure list was
> empty. The benchmark therefore does not assess synthesis, selectivity, ADMET,
> toxicity, pharmacokinetics, compound availability, or expert medicinal-
> chemistry judgement.
>
> All 19,588 official candidate records parsed successfully. Of these, 10,039
> passed both numerical limits and 9,549 failed at least one. The mutually
> exclusive failure counts were 2,433 for molecular weight only, 3,765 for cLogP
> only, and 3,351 for both; equivalently, 5,784 exceeded the molecular-weight
> limit and 7,116 exceeded the cLogP limit. The 91 included cards contain 18,205
> of the official candidate records. No salt stripping, neutralisation, or
> other structure-standardisation step was applied beyond RDKit parsing and
> canonical-SMILES calculation.

### QSAR reproducibility

> Three QSAR regressors were trained separately on each card using its 50
> visible support compounds and pChEMBL outcomes. Structures were represented
> by 2,048-bit binary Morgan fingerprints with radius 2, using the RDKit
> generator defaults without an added chirality flag. Dense `float32` arrays
> were supplied to the estimators. The random-forest regressor
> used 100 trees, `min_samples_leaf=1`, and `random_state=7`. Gradient boosting
> used `GradientBoostingRegressor(random_state=7)` with the remaining
> scikit-learn 1.8.0 defaults. Linear support-vector regression used
> `StandardScaler(with_mean=False)` followed by
> `SVR(kernel="linear", C=1.0)`. Each fitted model predicted every feasible
> candidate, which was ranked by descending predicted activity with candidate
> identifier as the deterministic tie-break. A similarity fallback was
> specified for cards with fewer than three measured training compounds, but it
> was not invoked because every included card had 50 support measurements.
> Descriptor calculation used RDKit 2026.3.1; the locked environment also used
> NumPy 2.4.4, pandas 3.0.2, and scikit-learn 1.8.0. No cross-validation,
> per-card tuning, or hidden candidate activity was used.

### LLM reproducibility

> The model matrix crossed 91 cards, two input interfaces, and three frozen
> provider conditions. The conditions were OpenAI
> `gpt-5.5-2026-04-23` with low reasoning, Anthropic
> `claude-opus-4-8` without extended thinking, and DeepSeek
> `deepseek-v4-pro` with thinking disabled as checked on 16 July 2026. Each used
> a 4,096-output-token cap and a direct-JSON instruction. OpenAI and DeepSeek
> used JSON-object response mode; Anthropic received the JSON contract in the
> prompt without a native structured-output parameter. Temperature was not
> explicitly set and no API seed was supplied. The basic interface supplied task and endpoint context,
> support identifiers, SMILES, molecular weight, cLogP, and measured support
> pChEMBL values, followed by candidate identifiers, SMILES, molecular weight,
> and cLogP. The descriptor-enriched interface additionally supplied TPSA,
> hydrogen-bond donor and acceptor counts, and rotatable-bond count. Both stated
> that higher pChEMBL was better and required an exactly ten-ID response.
> Candidate activities were never included.
>
> The corrected matrix contains one successful recorded provider attempt for
> each of 546 raw requests. Exact request hashes, prompts, raw response content,
> returned model identifiers, response identifiers, finish reasons, token
> usage, latency, and pricing-derived costs were cached. The six raw conditions
> used 14,780,538 tokens and cost USD 58.956716 under the frozen pricing table.
> Post-hoc repair reused those responses and made zero additional provider
> calls. SDK retries were disabled. Because the providers were not seeded, the
> cache—not an assumption of deterministic generation—supports exact replay.
> The frozen exact-request export has SHA256
> `50e518893b19d4a7efd64c62e08ab94d610815f8fb7518c9af4b64ff40b6f6c5`.

### Guarding and repair attribution

> The validator checked JSON shape, task identity, exact shortlist length,
> candidate-pool membership, duplicate identifiers, support-set exclusion, and
> molecular eligibility. For deterministic post-hoc repair, valid unique raw
> candidate identifiers were retained in their serialized response order.
> Empty positions were then filled from the fixed rule-based ranking, excluding
> candidates already retained, and the resulting action was validated again.
> Neither validation nor repair accessed hidden candidate activity.
> The fixed fallback score was
> \(0.45\max(0,1-|MW-350|/350)
> +0.35\max(0,1-|cLogP-2.5|/4.5)
> +0.20\max(0,1-|TPSA-75|/150)\).
> Feasible candidates were ranked by decreasing score with candidate identifier
> as the deterministic tie-break. TPSA was computed by the software fallback
> even for the basic LLM interface, where it was not shown to the model.
>
> “Cards repaired” counts any action whose output contract was modified.
> “Fallback-supplied positions” gives the more direct measure of scientific
> harness contribution: the number of final candidate identities that were not
> proposed in the raw response and were instead supplied by deterministic
> fallback. Rank normalization and correction of task or system metadata can
> therefore count as a repaired card without replacing a candidate.

| Provider and interface | Cards repaired | Cards with a replaced identity | Fallback-supplied final positions | Mean per repaired card; median (range) | Cards with all 10 positions supplied by fallback |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI, basic | 19/91 (20.88%) | 10/91 | 14/910 (1.54%) | 0.74; 1 (0–4) | 0 |
| OpenAI, descriptors | 23/91 (25.27%) | 10/91 | 15/910 (1.65%) | 0.65; 0 (0–4) | 0 |
| Anthropic, basic | 74/91 (81.32%) | 71/91 | 252/910 (27.69%) | 3.41; 2 (0–10) | 1 |
| Anthropic, descriptors | 69/91 (75.82%) | 68/91 | 229/910 (25.16%) | 3.32; 3 (0–10) | 1 |
| DeepSeek, basic | 83/91 (91.21%) | 81/91 | 534/910 (58.68%) | 6.43; 7 (0–10) | 30 |
| DeepSeek, descriptors | 69/91 (75.82%) | 69/91 | 355/910 (39.01%) | 5.14; 4 (1–10) | 12 |

The machine-readable version is
`paper/manuscript/revision_repair_attribution.csv`.

Suggested Results wording:

> Guarding made all final actions executable, but its contribution differed
> sharply among conditions. In the best OpenAI basic-interface condition,
> repair was invoked on 19 of 91 cards. Only ten cards received a replacement
> identity, and fallback supplied 14 of 910 final positions (1.54%). Thus the
> guarded score was not the raw LLM score, although most final candidate
> identities still came from the model. In contrast, fallback supplied
> 25.16–27.69% of final Anthropic positions and 39.01–58.68% of final DeepSeek
> positions. Thirty DeepSeek basic-interface cards received all ten final
> identities from fallback. Those guarded results primarily characterise a
> model-plus-deterministic-harness system and cannot be interpreted as the
> performance of the LLM alone.

### Feasible utility and cross-card comparability

> CARA supplies candidate activity as pChEMBL, the negative base-10 logarithm
> of molar activity, so all cards have a common numerical direction and unit:
> higher is more potent and a one-unit difference represents a ten-fold
> concentration difference. The endpoint labels nevertheless include IC50, Ki,
> EC50, and Potency, and assay conditions and activity distributions differ.
> These endpoints are therefore not treated as biologically interchangeable.
>
> Let \(s_{mcr}\) be the identifier returned by system \(m\) at position \(r\)
> on card \(c\), \(V_c\) the feasible candidate set, and \(y_{ic}\) hidden
> pChEMBL activity. Feasible utility was
> \(U_m(c)=\sum_{r=1}^{k} y_{s_{mcr},c}
> I[s_{mcr}\in V_c\ \text{and}\ s_{mcr}\notin
> \{s_{mc1},\ldots,s_{mc,r-1}\}]\).
> A missing, invalid, infeasible, or repeated entry contributed zero, and
> entries beyond the first \(k=10\) positions received no credit. Thus the
> first valid occurrence of an identifier can score, but a later duplicate
> cannot.
>
> The main comparison between systems A and B was not a biological comparison of
> card A with card B. It was the within-card difference
> \(\Delta_c=U_A(c)-U_B(c)\), calculated after both systems saw the same
> support evidence and candidate pool, followed by the equally weighted mean of
> the 91 card-level differences. For valid fixed-size top-10 actions, a constant
> assay-specific offset cancels in this paired contrast. For raw malformed
> actions, zero utility for an invalid position is an intentional penalty for
> wasting part of the fixed budget.
>
> The mean feasible-utility values are consequently benchmark summaries, not
> physical or clinical quantities. As a scale-robust secondary analysis, the
> report also gives NDCG@10, which normalises each card's ranking against its own
> ideal feasible ranking. The paired QSAR advantage was present for both
> feasible utility (1.003; 95% interval 0.405 to 1.647) and NDCG@10 (0.0087;
> 95% interval 0.0010 to 0.0165).

Avoid saying that bootstrapping “adjusts for inter-card complexity.” Pairing
controls shared card difficulty in a system contrast; bootstrapping estimates
uncertainty and does not make different endpoints biologically equivalent.

### Bootstrap analysis

> Each decision card was the resampling unit. Marginal confidence intervals for
> a single system's mean were based on 1,000 bootstrap samples using NumPy's
> default random-number generator with seed 7. Each sample drew 91 cards with
> replacement, calculated the mean metric, and the 2.5th and 97.5th percentiles
> of the 1,000 means formed the 95% percentile interval.
>
> Headline system comparisons used a paired bootstrap. First, the metric
> difference between two systems was calculated on each matched card. Then
> 2,000 samples of the 91 differences were drawn with replacement using seed 13.
> The reported effect is the observed mean card-level difference, and its 95%
> interval is the 2.5th to 97.5th percentile of the bootstrap mean differences.
> The procedure preserves pairing because both system scores from a card always
> move together. These intervals describe variation across the observed CARA
> cards; they do not correct for benchmark selection, model-selection
> multiplicity, or dependence beyond the card level.

The “best QSAR” and “best LLM” rows were selected using the same observed
benchmark before the key paired interval was calculated. The interval is
therefore a descriptive post-selection interval, not a multiplicity-adjusted
confirmatory test or a Bayesian posterior probability.

### Corrected main Results paragraph

> The hidden-outcome oracle reached mean feasible utility 79.563. Among
> deployable systems, linear support-vector QSAR ranked first at 74.966,
> followed by random-forest QSAR at 74.958 and gradient boosting at 74.750. The
> strongest final LLM pipeline was the OpenAI basic interface plus deterministic
> post-hoc repair at 73.964. Its underlying raw response stream achieved 72.966
> and issued a fully valid action on 72 of 91 cards. Linear support-vector QSAR
> exceeded the guarded LLM by 1.003 utility points in the paired card analysis
> (95% bootstrap interval 0.405 to 1.647). The guarded LLM exceeded the
> similarity baseline by 0.675 points, but that interval included zero (-0.103
> to 1.470). These corrected data support a QSAR-family lead; they do not
> establish added decision value from the tested LLM conditions.

This paragraph replaces every numerical statement in v0.5, including its
abstract, tables, figures, and conclusion.

### Discussion: comparison with existing literature

> The strength of per-assay QSAR is consistent with CARA's lead-optimisation
> results, in which models trained on assay-relevant examples performed strongly
> and performance varied across assays \cite{tian2024cara}. Variation among LLM
> interfaces and providers is also consistent with ChemLLMBench's finding that
> chemistry performance depends on the task and in-context setup
> \cite{guo2023chemllmbench}. ChemCrow and LLM4SD demonstrate that LLMs can be
> useful components or coordinators in hybrid chemistry systems
> \cite{bran2024chemcrow,zheng2025llm4sd}; neither implies that a raw LLM ranking
> should outperform a model trained directly on assay-local support data. The
> present result is therefore narrower: on this corrected retrospective
> top-10 benchmark, the tested guarded pipelines produced executable shortlists,
> but the strongest conventional QSAR retained a paired advantage.

### Limitations: replacement paragraph

> This study is a retrospective computational benchmark, not prospective lead
> optimisation. It includes all 91 CARA `LO_All` tasks that could support the
> stated top-10 action after simplified feasibility filtering, but it does not
> represent CARA virtual-screening tasks, lead-optimisation tasks with fewer
> than ten feasible candidates, or the full distribution of industrial
> projects. The constraints omit synthesis, availability, selectivity, ADMET,
> toxicity, pharmacokinetics, and multi-objective trade-offs, and no medicinal
> chemist comparator was included. Activity is a retrospective proxy for the
> value of testing a compound and is not therapeutic value. The source data are
> public, so prompt-time leakage was controlled but pre-training exposure cannot
> be excluded. Provider results are specific to the dated models, interfaces,
> prompts, and settings evaluated. These limitations preclude claims about
> prospective laboratory performance or LLMs in drug discovery generally.

### Conclusion: replacement wording

> Across all 91 eligible CARA lead-optimisation cards, the strongest
> assay-specific QSAR model outperformed the strongest tested guarded LLM
> pipeline on the paired primary outcome. Deterministic validation made final
> actions executable, but the amount of shortlist content supplied by fallback
> ranged from 1.54% to 58.68% across conditions. Guarded performance must
> therefore be reported as model-plus-harness performance alongside the raw
> model result. The study supports strong conventional comparators, paired
> card-level analysis, and explicit repair attribution when evaluating
> constrained LLM decision systems; it does not establish superiority or
> general utility of LLMs for prospective drug discovery.

## Required numerical replacements

Do not retain any v0.5 number. At minimum, replace:

| Quantity | Corrected value |
| --- | ---: |
| Official tasks considered | 100 |
| Included cards | 91 |
| Support compounds per card | 50 |
| Candidate-pool range / mean | 52–967 / 200.055 |
| Feasible-pool range / mean | 12–579 / 110.165 |
| Endpoint cards | 68 IC50; 17 Ki; 5 EC50; 1 Potency |
| Oracle utility | 79.5626 |
| QSAR SVM utility | 74.9664 |
| QSAR random-forest utility | 74.9580 |
| QSAR gradient-boosting utility | 74.7499 |
| Similarity utility | 73.2882 |
| Best guarded LLM utility | 73.9637 |
| Same response stream, raw utility | 72.9664 |
| Same response stream, raw whole-action validity | 72/91 (79.12%) |
| QSAR minus guarded LLM | 1.0027 (95% interval 0.4049–1.6475) |
| Guarded LLM minus similarity | 0.6754 (95% interval -0.1033–1.4702) |
| Total raw provider requests | 546 |
| Pricing-derived cost | USD 58.956716 |

Round consistently in prose and tables. Preserve full precision in
machine-readable artifacts.

## Submission checklist

1. Remove every v0.5 table, figure, checksum, model name, and result derived
   from `cara_lo_paper_50`.
2. Use Claude Opus 4.8, not the historical Opus 4.7 condition.
3. Label rows “raw LLM” and “LLM + deterministic post-hoc repair”; never shorten
   a repaired row to the model name alone.
4. Use whole-action validity for “valid as issued.” Keep valid-selection
   fraction only as a separately named partial-credit diagnostic.
5. Add the fallback-supplied-position table, not only repair rate.
6. Explain utility using paired within-card differences and NDCG@10; do not
   claim that endpoint biology is interchangeable.
7. State all bootstrap settings and avoid implying that resampling removes
   selection bias.
8. Keep the no-medicinal-chemist, simplified-constraints, public-data-exposure,
   and no-prospective-validation limitations.
9. Correct the methods sentence that currently says “LLM minus best QSAR”:
   the reported positive 1.0027 effect is **QSAR minus LLM**.
10. Freeze the completed full matrix into the submission branch, regenerate
    tables and figures from machine-readable artifacts, and reproduce the
    report from a clean checkout before submission. **Completed; see the final
    gate log under Evidence and provenance.**

## Evidence and provenance

- Corrected system-input card SHA256:
  `c18e66c726bb26f8afc3ba8422b21ec327444560d92750421f0dc44a2f393d9e`
- Corrected scorer-outcome SHA256:
  `96b5d6060e3c75dda34d835fd166fd074ca5621c18924aa0ea2714acba173ff4`
- Corrected inputs:
  `data/releases/v0.1.0/system_input_cards.jsonl`
- Scorer-only outcomes:
  `data/releases/v0.1.0/scorer_outcomes.jsonl`
- QSAR implementation:
  `src/specguard_chem_v2/systems/baselines.py`
- Fingerprints and descriptors:
  `src/specguard_chem_v2/chem/descriptors.py`
- Bootstrap implementation:
  `src/specguard_chem_v2/scoring.py` and
  `src/specguard_chem_v2/reports.py`
- Full result table after integration:
  `release/v0.1.0/experiments/llm/comparison/system_comparison.csv`
- Paired headline contrasts after integration:
  `release/v0.1.0/experiments/llm/comparison/paired_bootstrap_key_deltas.csv`
- Raw and repaired traces after integration:
  `release/v0.1.0/experiments/llm/matrix/`
- Final clean-checkout reproduction log:
  `plans/logs/2026-07-28-0040-final-manuscript-and-reproduction-gate.md`
