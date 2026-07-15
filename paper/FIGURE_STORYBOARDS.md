# Figure Storyboards

This file is for workshopping figure structure before final rendering. Diagrams
should stay easy to edit in plain text. Use these as the system of record for
layout and wording until a figure is ready for production artwork.

## Figure 1: Frozen Decision Card Anatomy

Goal: explain what a decision card contains without tying the figure to one LLM
prompt implementation.

### ASCII Draft

```text
Example frozen decision card
CARA_LO_CHEMBL2328568_IC50_0001

+--------------------------------------------------------------------------+
| CARD HEADER                                                              |
| task_id: CARA_LO_CHEMBL2328568_IC50_0001                                 |
| assay_context: source=CARA; assay_id=CHEMBL2328568_IC50                  |
| budget_k: 10; support_size: 50; candidate_pool_size: 967; feasible: 618  |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
| SUPPORT SET                                                              |
| Visible to deployable systems: id, SMILES, support activity, descriptors |
|                                                                          |
| id          smiles                         activity    descriptors        |
| CHEMBL...   CC(C)(C)c1[nH]...              6.44        MW, cLogP, TPSA... |
| CHEMBL...   Cc1c(F)ccc2[nH]...             8.15        MW, cLogP, TPSA... |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
| CANDIDATE POOL                                                           |
| Visible: id, SMILES, descriptors                                         |
| Hidden from deployable systems: candidate activity                        |
|                                                                          |
| id          smiles                         activity     descriptors       |
| CHEMBL...   COc1cc(CN...)...               scorer-only  MW, cLogP, TPSA...|
| CHEMBL...   COc1cc(CNc...)...              scorer-only  MW, cLogP, TPSA...|
+--------------------------------------------------------------------------+

+-------------------------------------+    +------------------------------+
| HARD CONSTRAINTS                    |    | OUTPUT SCHEMA                |
| exactly k                           |    | rank: integer                |
| candidate pool only                 |    | candidate_id: string         |
| no duplicates                       |    | confidence: optional number  |
| exclude support                     |    +------------------------------+
| MW <= 500                           |
| cLogP <= 4.5                        |
| forbidden SMARTS: []                |
+-------------------------------------+

+--------------------------------------------------------------------------+
| LEAKAGE BOUNDARY                                                         |
| Support activity is input. Candidate activity is stored for scoring only. |
| Only the oracle upper-bound control uses hidden candidate activity.        |
+--------------------------------------------------------------------------+
```

### Mermaid Draft

```mermaid
flowchart TB
    Header["Card header<br/>task_id, assay_context, budget_k<br/>support_size=50, candidate_pool_size=967, feasible=618"]

    Support["Support set<br/>id + SMILES + visible activity + descriptors"]
    Candidate["Candidate pool<br/>id + SMILES + descriptors<br/><b>candidate activity: scorer-only</b>"]

    Constraints["Hard constraints<br/>exactly k<br/>candidate pool only<br/>no duplicates<br/>exclude support<br/>MW <= 500<br/>cLogP <= 4.5"]
    Output["Output schema<br/>rank<br/>candidate_id<br/>confidence"]
    Scoring["Scorer-only fields<br/>hidden candidate activity<br/>used for utility and NDCG@10"]

    Header --> Support
    Header --> Candidate
    Header --> Constraints
    Header --> Output
    Candidate -. hidden labels .-> Scoring
```

## Figure 2: Benchmark Pipeline

Goal: explain the full evaluation flow, keeping it distinct from Figure 1.
Use accessible wording without making the boxes wordy.

### ASCII Draft

Use this as a wording sketch. The Mermaid draft below is the clearer layout
reference because each method card feeds the top-10 shortlist.

```text
SOURCE DATA
CARA/ChEMBL lead-optimisation records
        |
        v
DECISION CARDS
50 fixed test cases
contents: known compounds, candidate pool, rules, budget
        |
        v
METHODS COMPARED
        |
        +--> SIMPLE RULES
        |    random, property rules, similarity
        |
        +--> QSAR
        |    standard chemistry prediction models
        |
        +--> LLM
        |    language model alone
        |
        +--> GUARDED LLM
        |    language model plus validation/repair
        |
        +--> ORACLE
             upper bound; sees hidden activity
                 |
                 v
TOP-10 SHORTLIST
ranked candidate IDs
        |
        v
        +--> COMPLIANCE CHECK
        |    did the shortlist follow the rules?
        |
        +--> HIDDEN-ACTIVITY SCORE
             were the chosen compounds active?
                 |
                 v
RESULTS
leaderboard, raw/final LLM comparison, paired differences

Notes:
candidate activity is hidden from tested methods
oracle is reported separately as an upper bound
```

Even more compact version:

```text
Source data
        |
        v
50 decision cards
        |
        v
Methods choose 10 candidates
        |
        v
Shortlists checked and scored
        |
        v
Results
```

### Mermaid Draft

```mermaid
flowchart TB
    A["SOURCE DATA<br/>CARA/ChEMBL lead-optimisation records"]
    B["DECISION CARDS<br/>50 fixed test cases<br/>known compounds, candidate pool, rules, budget"]
    C["METHODS COMPARED<br/>same cards given to each method"]
    M1["SIMPLE RULES<br/>random, property rules, similarity"]
    M2["QSAR<br/>standard chemistry prediction models"]
    M3["LANGUAGE MODEL<br/>model chooses IDs directly"]
    M4["GUARDED LANGUAGE MODEL<br/>output checked and repaired"]
    M5["ORACLE<br/>upper bound; sees hidden activity"]
    D["TOP-10 SHORTLIST<br/>ranked candidate IDs"]
    E1["COMPLIANCE CHECK<br/>did the shortlist follow the rules?"]
    E2["HIDDEN-ACTIVITY SCORE<br/>were the chosen compounds active?"]
    F["RESULTS<br/>leaderboard<br/>raw/final LLM comparison<br/>paired differences"]

    A --> B --> C
    C --> M1
    C --> M2
    C --> M3
    C --> M4
    C -.-> M5

    M1 --> D
    M2 --> D
    M3 --> D
    M4 --> D
    M5 -.-> D

    D --> E1
    D --> E2
    E1 --> F
    E2 --> F
```
