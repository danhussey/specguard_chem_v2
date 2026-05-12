# High-Reasoning Interface Options

The current full-pool prompt can exceed 100k input tokens for a single
tool-summary card. Direct JSON can handle this better than high-reasoning modes,
but high-reasoning/thinking models need a smaller or staged interface before
they are suitable for full paper-scale runs.

## Current Prompt Contents

For each decision card, the LLM request currently includes:

- task ID, system name, provider/model config, and generation settings;
- assay context;
- support set with tested compound IDs, SMILES, and observed activity values;
- candidate pool with IDs, SMILES, MW, cLogP, and for tool conditions TPSA, HBD,
  HBA, and rotatable-bond counts;
- hard constraints as JSON;
- response contract and budget `k`.

The hidden candidate activity values are not included.

## Compression Options

- Remove repeated provider/generation metadata from the user prompt; keep it in
  trace metadata.
- Replace support-set raw SMILES with compact learned summaries: top actives,
  inactive examples, descriptor ranges, and nearest-neighbour signals.
- Replace full candidate JSON with a candidate table that omits fields not used
  by the model condition.
- Use two-stage reranking: cheap QSAR/similarity produces an auditable shortlist,
  high-reasoning model reranks the shortlist, and scoring reports both full-pool
  oracle regret and shortlist oracle regret.
- Bucket candidates by similarity, property feasibility, QSAR score, and
  diversity, then show representative candidates plus the final shortlist.
- Keep full-pool IDs available to deterministic tools, but avoid pasting every
  candidate's full descriptor row into the reasoning model context.

## Evaluation Guardrails

Any compressed or staged interface is a new experimental condition. It must not
be mixed with the original full-pool results without clear labelling. Report:

- full-pool oracle regret;
- shortlist oracle regret when a shortlist is used;
- raw model metrics;
- final guarded-system metrics;
- compression or shortlist provenance.
