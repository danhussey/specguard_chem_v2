from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import pandas as pd

from .io import read_json


ABLATION_PAIRS = [
    ("bare_llm", "llm_validator", "validator_delta"),
    ("llm_tools", "llm_tools_validator", "tools_validator_delta"),
    ("bare_llm", "llm_tools", "tools_delta"),
]


def compare_run_summaries(summary_paths: list[Path], out_dir: Path) -> pd.DataFrame:
    rows = [read_json(path) for path in summary_paths]
    frame = pd.DataFrame(rows)
    if not frame.empty and "system_name" in frame.columns:
        frame = frame.sort_values(["feasible_utility", "compliance_rate"], ascending=[False, False])
    out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_dir / "system_comparison.csv", index=False)
    frame.to_json(out_dir / "system_comparison.json", orient="records", indent=2)
    _write_leaderboard_slices(frame, out_dir)
    _write_metric_winners(frame, out_dir)
    _write_ablation_table(frame, out_dir)
    return frame


def _is_oracle_system(system_name: object) -> bool:
    return str(system_name).startswith("oracle_")


def _write_leaderboard_slices(frame: pd.DataFrame, out_dir: Path) -> None:
    if frame.empty or "system_name" not in frame.columns:
        frame.to_csv(out_dir / "primary_leaderboard.csv", index=False)
        frame.to_csv(out_dir / "oracle_controls.csv", index=False)
        return
    oracle_mask = frame["system_name"].map(_is_oracle_system)
    frame.loc[~oracle_mask].to_csv(out_dir / "primary_leaderboard.csv", index=False)
    frame.loc[oracle_mask].to_csv(out_dir / "oracle_controls.csv", index=False)


def _write_metric_winners(frame: pd.DataFrame, out_dir: Path) -> None:
    metrics = [
        ("feasible_utility", False),
        ("raw_feasible_utility", False),
        ("ndcg_at_k", False),
        ("raw_ndcg_at_k", False),
        ("compliance_rate", False),
        ("raw_compliance_rate", False),
        ("constrained_regret", True),
        ("schema_error_rate", True),
        ("raw_schema_error_rate", True),
    ]

    def _winner_rows(source: pd.DataFrame) -> list[dict[str, object]]:
        local_rows: list[dict[str, object]] = []
        if source.empty or "system_name" not in source.columns:
            return local_rows
        for metric, lower_is_better in metrics:
            if metric not in source.columns:
                continue
            metric_frame = source[["system_name", metric]].dropna()
            if metric_frame.empty:
                continue
            selected = metric_frame.sort_values(metric, ascending=lower_is_better).iloc[0]
            local_rows.append(
                {
                    "metric": metric,
                    "winner": selected["system_name"],
                    "value": selected[metric],
                    "lower_is_better": lower_is_better,
                }
            )
        return local_rows

    rows = _winner_rows(frame)
    pd.DataFrame(rows).to_csv(out_dir / "metric_winners.csv", index=False)
    if frame.empty or "system_name" not in frame.columns:
        pd.DataFrame([]).to_csv(out_dir / "metric_winners_primary.csv", index=False)
        return
    primary = frame.loc[~frame["system_name"].map(_is_oracle_system)]
    pd.DataFrame(_winner_rows(primary)).to_csv(out_dir / "metric_winners_primary.csv", index=False)


def _write_ablation_table(frame: pd.DataFrame, out_dir: Path) -> None:
    rows: list[dict[str, object]] = []
    if frame.empty or "system_name" not in frame.columns:
        pd.DataFrame(rows).to_csv(out_dir / "ablation_deltas.csv", index=False)
        return
    by_system = {str(row["system_name"]): row for _, row in frame.iterrows()}
    metrics = [
        "feasible_utility",
        "raw_feasible_utility",
        "compliance_rate",
        "raw_compliance_rate",
        "constrained_regret",
        "schema_error_rate",
        "raw_schema_error_rate",
        "repaired_rate",
        "repaired_from_empty_rate",
    ]

    pairs: list[tuple[str, str, str]] = []
    for before, after, label in ABLATION_PAIRS:
        pairs.append((before, after, label))
        suffixes = {
            system_name.removeprefix(f"{before}__")
            for system_name in by_system
            if system_name.startswith(f"{before}__")
        }
        for suffix in sorted(suffixes):
            variant_before = f"{before}__{suffix}"
            variant_after = f"{after}__{suffix}"
            if variant_after in by_system:
                pairs.append((variant_before, variant_after, f"{label}__{suffix}"))

    for before, after, label in pairs:
        if before not in by_system or after not in by_system:
            continue
        row: dict[str, object] = {"ablation": label, "before": before, "after": after}
        for metric in metrics:
            if metric not in frame.columns:
                continue
            before_value = by_system[before].get(metric)
            after_value = by_system[after].get(metric)
            if pd.isna(before_value) or pd.isna(after_value):
                row[f"{metric}_delta"] = None
            else:
                row[f"{metric}_delta"] = float(after_value) - float(before_value)
        rows.append(row)
    pd.DataFrame(rows).to_csv(out_dir / "ablation_deltas.csv", index=False)


def make_frontier_plot(comparison_csv: Path, out_dir: Path) -> Path:
    import matplotlib.pyplot as plt

    frame = pd.read_csv(comparison_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    if not frame.empty:
        ax.scatter(frame["compliance_rate"], frame["feasible_utility"], s=70)
        for _, row in frame.iterrows():
            ax.annotate(
                str(row.get("system_name", "")),
                (float(row["compliance_rate"]), float(row["feasible_utility"])),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8,
            )
    ax.set_xlabel("Compliance rate")
    ax.set_ylabel("Feasible utility")
    ax.set_title("Compliance-Utility Frontier")
    ax.set_xlim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    output = out_dir / "compliance_utility_frontier.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)
    return output


def _format_float(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    available = [column for column in columns if column in frame.columns]
    if frame.empty or not available:
        return "_No rows._\n"
    header = "| " + " | ".join(available) + " |"
    separator = "| " + " | ".join(["---"] * len(available)) + " |"
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in available:
            value = row[column]
            cells.append(_format_float(value) if column != "system_name" else str(value))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows]) + "\n"


SYSTEM_LABELS = {
    "oracle_valid_topk": "Oracle upper-bound",
    "random_valid": "Random valid baseline",
    "rules_only": "Rule/desirability baseline",
    "similarity_to_best_active": "Similarity-to-best-active baseline",
    "qsar_rf": "QSAR random forest",
    "qsar_gbt": "QSAR gradient boosting",
    "qsar_svm": "QSAR linear SVR",
    "bare_llm": "Bare LLM",
    "llm_tools": "LLM plus tool summaries",
    "llm_validator": "LLM plus validator",
    "llm_tools_validator": "LLM plus tools and validator",
}


SYSTEM_DESCRIPTIONS = {
    "oracle_valid_topk": "Non-deployable upper-bound control that ranks valid candidates using hidden activity values.",
    "random_valid": "Samples valid candidates at random after deterministic feasibility filtering.",
    "rules_only": "Applies deterministic constraints, then ranks by simple molecular-property desirability around MW 350, cLogP 2.5, and TPSA 75.",
    "similarity_to_best_active": "Ranks feasible candidates by Morgan-fingerprint Tanimoto similarity to the most active support compound.",
    "qsar_rf": "Trains a random forest regressor on support-set Morgan fingerprints and measured activity, then ranks feasible candidates by predicted activity.",
    "qsar_gbt": "Trains a gradient-boosting regressor on support-set Morgan fingerprints and measured activity, then ranks feasible candidates by predicted activity.",
    "qsar_svm": "Trains a sparse-scaled linear-kernel support-vector regressor on support-set Morgan fingerprints and measured activity, then ranks feasible candidates by predicted activity.",
    "bare_llm": "Prompts the model to return ranked candidate IDs directly, with no deterministic repair.",
    "llm_tools": "Adds computed tool-summary fields to the candidate rows before prompting the model.",
    "llm_validator": "Checks raw model output and deterministically repairs invalid or missing slots where possible, without hidden activity.",
    "llm_tools_validator": "Combines tool-summary candidate rows with deterministic validation and repair.",
}


CONDITION_DESCRIPTIONS = {
    "frontier_selector": "Direct-JSON frontier condition: final-answer JSON prompting with no explicit extended-thinking mode where avoidable.",
    "frontier": "Original frontier/high-reasoning or provider-default frontier condition.",
    "fast": "Lower-latency/lower-cost provider condition.",
}


METRIC_DESCRIPTIONS = {
    "feasible_utility": "Final utility after any validator repair. Sums hidden activity for selected candidates that satisfy hard constraints. Higher is better.",
    "raw_feasible_utility": "Utility before validator repair. This is the closer measure of raw LLM behavior. Higher is better.",
    "ndcg_at_k": "Final ranking quality using hidden activity as graded relevance. 1.0 is ideal.",
    "raw_ndcg_at_k": "NDCG before validator repair.",
    "constrained_regret": "Oracle valid top-k utility minus observed feasible utility. Lower is better.",
    "compliance_rate": "Fraction of requested selections that are valid after final repair, if repair applies.",
    "raw_compliance_rate": "Fraction of requested selections that are valid before validator repair.",
    "schema_error_rate": "Fraction of cards with final output schema or contract errors.",
    "raw_schema_error_rate": "Fraction of cards with raw output schema or contract errors.",
    "repaired_rate": "Fraction of cards where the final validator changed the raw model output.",
    "repaired_from_empty_rate": "Fraction of cards where an empty raw model selection was repaired. Near zero is expected for a usable LLM interface.",
}


def _base_system_name(system_name: str) -> str:
    return system_name.split("__", 1)[0]


def _condition_name(system_name: str) -> str:
    if "__" not in system_name:
        return ""
    return system_name.split("__", 1)[1]


def _system_group(system_name: str) -> str:
    base = _base_system_name(system_name)
    if _is_oracle_system(system_name):
        return "Oracle"
    if base.startswith("qsar_"):
        return "QSAR"
    if base in {"random_valid", "rules_only", "similarity_to_best_active"}:
        return "Baseline"
    if base.startswith("llm_") or base == "bare_llm":
        return "LLM"
    return "Other"


def _system_provider(system_name: str) -> str:
    condition = _condition_name(system_name)
    for provider in ["openai", "anthropic", "deepseek"]:
        if condition.startswith(provider):
            return provider
    return ""


def _condition_description(condition: str) -> str:
    if not condition:
        return ""
    for suffix, description in CONDITION_DESCRIPTIONS.items():
        if condition.endswith(suffix):
            return description
    return f"Model/run condition: {condition}."


def _system_description(system_name: str) -> str:
    base = _base_system_name(system_name)
    description = SYSTEM_DESCRIPTIONS.get(base, "System row from the comparison table.")
    condition = _condition_description(_condition_name(system_name))
    if condition:
        return f"{description} {condition}"
    return description


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dashboard_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    numeric_columns = [
        "feasible_utility",
        "raw_feasible_utility",
        "ndcg_at_k",
        "raw_ndcg_at_k",
        "constrained_regret",
        "compliance_rate",
        "raw_compliance_rate",
        "schema_error_rate",
        "raw_schema_error_rate",
        "repaired_rate",
        "repaired_from_empty_rate",
    ]
    for _, row in frame.iterrows():
        system_name = str(row.get("system_name", ""))
        base = _base_system_name(system_name)
        output: dict[str, object] = {
            "system_name": system_name,
            "base_system": base,
            "display_name": SYSTEM_LABELS.get(base, system_name),
            "condition": _condition_name(system_name),
            "provider": _system_provider(system_name),
            "group": _system_group(system_name),
            "description": _system_description(system_name),
        }
        for column in numeric_columns:
            output[column] = _safe_float(row.get(column)) if column in frame.columns else None
        rows.append(output)
    return rows


def _json_for_html(value: object) -> str:
    return json.dumps(value, sort_keys=True).replace("<", "\\u003c")


def write_results_dashboard(
    comparison_csv: Path,
    out_dir: Path,
    *,
    title: str = "SpecGuard-Chem v2 Results Dashboard",
) -> Path:
    frame = pd.read_csv(comparison_csv)
    if not frame.empty and "system_name" in frame.columns:
        frame = frame.sort_values(["feasible_utility", "compliance_rate"], ascending=[False, False])
    rows = _dashboard_rows(frame)
    generated_at = datetime.now(timezone.utc).isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "RESULTS_DASHBOARD.html"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #64717f;
      --line: #d7ddd8;
      --oracle: #111827;
      --qsar: #2563eb;
      --baseline: #0f766e;
      --llm: #b91c1c;
      --other: #6b7280;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    h1 {{ margin: 0 0 6px; font-size: 24px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 17px; }}
    h3 {{ margin: 0 0 8px; font-size: 14px; }}
    .subtle {{ color: var(--muted); }}
    main {{ max-width: 1480px; margin: 0 auto; padding: 22px 24px 36px; }}
    .grid {{ display: grid; gap: 16px; }}
    .summary-grid {{ grid-template-columns: repeat(4, minmax(180px, 1fr)); }}
    .plot-grid {{ grid-template-columns: minmax(560px, 1.4fr) minmax(340px, 0.9fr); }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 1px 2px rgba(31, 41, 51, 0.04);
    }}
    .stat-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .stat-value {{ margin-top: 6px; font-size: 24px; font-weight: 700; }}
    .stat-note {{ margin-top: 4px; color: var(--muted); font-size: 12px; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 10px 16px; margin: 10px 0 0; }}
    .legend span {{ display: inline-flex; align-items: center; gap: 6px; color: var(--muted); }}
    .swatch {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }}
    select, input {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 7px 9px;
      background: #ffffff;
      color: var(--ink);
    }}
    svg {{ width: 100%; height: auto; display: block; }}
    .axis text {{ fill: var(--muted); font-size: 11px; }}
    .axis line, .axis path {{ stroke: var(--line); }}
    .bar-row {{ display: grid; grid-template-columns: minmax(180px, 1fr) 120px; gap: 10px; align-items: center; margin: 8px 0; }}
    .bar-track {{ height: 18px; background: #eef1ed; border-radius: 5px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 5px; }}
    .bar-value {{ text-align: right; font-variant-numeric: tabular-nums; color: var(--muted); }}
    .bar-label {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .flow {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; align-items: stretch; }}
    .flow-step {{ border: 1px solid var(--line); border-radius: 7px; padding: 10px; background: #fbfcfa; min-height: 86px; }}
    .flow-step strong {{ display: block; margin-bottom: 4px; }}
    .flow-step small {{ color: var(--muted); }}
    .term {{
      border-bottom: 1px dotted var(--muted);
      cursor: help;
      text-decoration: none;
    }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; background: #fbfcfa; position: sticky; top: 0; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .pill {{ display: inline-block; border-radius: 999px; padding: 2px 7px; font-size: 12px; color: #fff; }}
    .Oracle {{ background: var(--oracle); }}
    .QSAR {{ background: var(--qsar); }}
    .Baseline {{ background: var(--baseline); }}
    .LLM {{ background: var(--llm); }}
    .Other {{ background: var(--other); }}
    details {{ margin-top: 16px; }}
    summary {{ cursor: pointer; font-weight: 600; }}
    code {{ background: #edf0ec; padding: 1px 4px; border-radius: 4px; }}
    @media (max-width: 980px) {{
      .summary-grid, .plot-grid, .flow {{ grid-template-columns: 1fr; }}
      main {{ padding: 16px; }}
      header {{ padding: 22px 18px 14px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <div class="subtle">Generated at <code>{escape(generated_at)}</code> from <code>{escape(str(comparison_csv))}</code></div>
  </header>
  <main>
    <section class="grid summary-grid" id="summaryCards"></section>

    <section class="panel" style="margin-top:16px">
      <h2><span class="term" title="The reproducible path from frozen decision cards to scored result artifacts.">Run Pipeline</span></h2>
      <div class="flow">
        <div class="flow-step"><strong><span class="term" title="One benchmark instance: support compounds, candidate pool, hard constraints, budget k, and hidden scorer-only activity values.">1. Decision cards</span></strong><small>Support set, candidate pool, hard constraints, and budget k.</small></div>
        <div class="flow-step"><strong>2. System output</strong><small>Baselines or LLMs return ranked candidate IDs.</small></div>
        <div class="flow-step"><strong><span class="term" title="Scores the model output before deterministic validator repair, so repaired behavior is not mistaken for raw model behavior.">3. Raw audit</span></strong><small>Raw LLM selections are scored before repair where available.</small></div>
        <div class="flow-step"><strong><span class="term" title="Deterministic harness logic for schema, candidate IDs, duplicates, support-set exclusion, and RDKit/property constraints. It does not use hidden activity.">4. Validator</span></strong><small>Deterministic schema, ID, duplicate, support-exclusion, and RDKit/property checks.</small></div>
        <div class="flow-step"><strong>5. Scoring</strong><small>Utility, compliance, regret, repair rate, and frontier plots.</small></div>
      </div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px">
      <div class="panel">
        <h2><span class="term" title="Scatter plot separating specification compliance on the x-axis from medicinal-chemistry decision utility on the y-axis.">Compliance-Utility Frontier</span></h2>
        <div class="controls">
          <label>Y metric
            <select id="yMetric">
              <option value="feasible_utility">Final feasible utility</option>
              <option value="raw_feasible_utility">Raw feasible utility</option>
              <option value="ndcg_at_k">Final NDCG@k</option>
              <option value="raw_ndcg_at_k">Raw NDCG@k</option>
            </select>
          </label>
          <label>X metric
            <select id="xMetric">
              <option value="compliance_rate">Final compliance</option>
              <option value="raw_compliance_rate">Raw compliance</option>
              <option value="schema_error_rate">Final schema error</option>
              <option value="raw_schema_error_rate">Raw schema error</option>
            </select>
          </label>
          <label>X scale
            <select id="xScale">
              <option value="auto" selected>Auto log for clustered rates</option>
              <option value="linear">Linear</option>
              <option value="log_gap">Log gap to 1.0</option>
              <option value="log_value">Log value</option>
            </select>
          </label>
        </div>
        <div id="scatter"></div>
        <div class="legend" id="legend"></div>
      </div>
      <div class="panel">
        <h2>Top <span class="term" title="Primary systems exclude oracle controls. They are the deployable or prospectively runnable systems used for main comparisons.">Primary Systems</span></h2>
        <div id="leaderboard"></div>
      </div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px">
      <div class="panel">
        <h2>Raw-to-Final Repair Delta</h2>
        <p class="subtle">Positive bars mean deterministic repair increased final feasible utility relative to raw model output.</p>
        <div id="repairBars"></div>
      </div>
      <div class="panel">
        <h2>Label Guide</h2>
        <p><strong><span class="term" title="Quantitative structure-activity relationship models: conventional molecular ML regressors, not language models.">QSAR models:</span></strong> all three train on support-set Morgan fingerprints and measured activity, then rank feasible candidates by predicted activity.</p>
        <p><code>qsar_rf</code> is a random forest regressor; <code>qsar_gbt</code> is a gradient-boosting regressor; <code>qsar_svm</code> is a sparse-scaled linear-kernel support-vector regressor.</p>
        <p><strong><span class="term" title="Deterministic harness logic, not a model and not an activity oracle.">Validator:</span></strong> deterministic harness checks and repair. It does not inspect hidden activity values.</p>
        <p><strong><span class="term" title="A non-deployable control that uses hidden candidate activity values.">Oracle:</span></strong> hidden-activity upper bound used only to show remaining decision headroom.</p>
        <p><strong><span class="term" title="The current prompt profile: final answer JSON only, without relying on visible chain-of-thought text.">Direct JSON:</span></strong> final-answer JSON prompting designed to avoid visible-output budget failures.</p>
      </div>
    </section>

    <section class="panel" style="margin-top:16px">
      <h2>System Table</h2>
      <div class="controls">
        <label>Group
          <select id="groupFilter">
            <option value="all">All groups</option>
            <option value="Oracle">Oracle</option>
            <option value="QSAR">QSAR</option>
            <option value="Baseline">Baseline</option>
            <option value="LLM">LLM</option>
          </select>
        </label>
        <label>Search
          <input id="searchBox" type="search" placeholder="system, provider, metric label">
        </label>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>System</th>
              <th>Group</th>
              <th><span class="term" title="{escape(METRIC_DESCRIPTIONS['feasible_utility'])}">Utility</span></th>
              <th><span class="term" title="{escape(METRIC_DESCRIPTIONS['raw_feasible_utility'])}">Raw utility</span></th>
              <th><span class="term" title="{escape(METRIC_DESCRIPTIONS['ndcg_at_k'])}">NDCG</span></th>
              <th><span class="term" title="{escape(METRIC_DESCRIPTIONS['compliance_rate'])}">Compliance</span></th>
              <th><span class="term" title="{escape(METRIC_DESCRIPTIONS['raw_compliance_rate'])}">Raw compliance</span></th>
              <th><span class="term" title="{escape(METRIC_DESCRIPTIONS['repaired_rate'])}">Repaired</span></th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody id="systemRows"></tbody>
        </table>
      </div>
    </section>

    <details class="panel">
      <summary>Metric definitions</summary>
      <dl id="metricDefinitions"></dl>
    </details>
  </main>
  <script>
    const rows = {_json_for_html(rows)};
    const metricHelp = {_json_for_html(METRIC_DESCRIPTIONS)};
    const colors = {{Oracle: "#111827", QSAR: "#2563eb", Baseline: "#0f766e", LLM: "#b91c1c", Other: "#6b7280"}};

    const fmt = (value, digits = 3) => value === null || value === undefined || Number.isNaN(value) ? "" : Number(value).toFixed(digits);
    const primaryRows = () => rows.filter(row => row.group !== "Oracle");
    const byMetricDesc = metric => [...rows].filter(row => row[metric] !== null).sort((a, b) => b[metric] - a[metric]);

    function bestBy(metric, filterFn = () => true) {{
      return rows.filter(row => filterFn(row) && row[metric] !== null).sort((a, b) => b[metric] - a[metric])[0] || null;
    }}

    function renderSummary() {{
      const oracle = bestBy("feasible_utility", row => row.group === "Oracle");
      const primary = bestBy("feasible_utility", row => row.group !== "Oracle");
      const rawLlm = bestBy("raw_feasible_utility", row => row.group === "LLM");
      const repairSensitive = rows.filter(row => row.repaired_rate !== null && row.repaired_rate >= 0.1).length;
      const cards = [
        ["Best primary utility", primary ? fmt(primary.feasible_utility) : "", primary ? primary.system_name : ""],
        ["Oracle utility", oracle ? fmt(oracle.feasible_utility) : "", "Upper bound, not deployable"],
        ["Best raw LLM utility", rawLlm ? fmt(rawLlm.raw_feasible_utility) : "", rawLlm ? rawLlm.system_name : ""],
        ["Repair-sensitive rows", String(repairSensitive), "Rows with repaired_rate >= 0.10"]
      ];
      document.getElementById("summaryCards").innerHTML = cards.map(card => `
        <div class="panel">
          <div class="stat-label">${{card[0]}}</div>
          <div class="stat-value">${{card[1]}}</div>
          <div class="stat-note">${{card[2]}}</div>
        </div>`).join("");
    }}

    function scale(value, inMin, inMax, outMin, outMax) {{
      if (inMax === inMin) return (outMin + outMax) / 2;
      return outMin + ((value - inMin) / (inMax - inMin)) * (outMax - outMin);
    }}

    function effectiveXScale(metric, requested) {{
      if (requested !== "auto") return requested;
      if (metric.includes("compliance")) return "log_gap";
      if (metric.includes("schema_error")) return "log_value";
      return "linear";
    }}

    function transformX(value, metric, mode) {{
      const epsilon = 1e-4;
      if (mode === "log_gap") return -Math.log10(Math.max(epsilon, 1 - value));
      if (mode === "log_value") return Math.log10(Math.max(epsilon, value));
      return value;
    }}

    function xTickValues(metric, mode) {{
      if (mode === "log_gap") return [0, 0.5, 0.9, 0.99, 0.999, 1.0];
      if (mode === "log_value") return [0, 0.001, 0.01, 0.1, 1.0];
      return [0, 0.25, 0.5, 0.75, 1.0];
    }}

    function xTickLabel(value, mode) {{
      if (mode === "log_gap") return value === 1 ? "1.000" : fmt(value, value >= 0.99 ? 3 : 2);
      if (mode === "log_value") return value === 0 ? "0" : String(value);
      return fmt(value, 2);
    }}

    function xAxisLabel(metric, mode) {{
      if (mode === "log_gap") return `${{metric}} (log distance from 1.0; right is better)`;
      if (mode === "log_value") return `${{metric}} (log value)`;
      return metric;
    }}

    function renderScatter() {{
      const xMetric = document.getElementById("xMetric").value;
      const yMetric = document.getElementById("yMetric").value;
      const xMode = effectiveXScale(xMetric, document.getElementById("xScale").value);
      const data = rows.filter(row => row[xMetric] !== null && row[yMetric] !== null);
      const width = 860, height = 500, margin = {{left: 74, right: 24, top: 20, bottom: 58}};
      const xVals = data.map(row => transformX(row[xMetric], xMetric, xMode));
      const yVals = data.map(row => row[yMetric]);
      const xMin = Math.min(...xVals), xMax = Math.max(...xVals);
      const yMin = Math.min(0, ...yVals), yMax = Math.max(...yVals) * 1.06;
      const x = value => scale(value, xMin, xMax, margin.left, width - margin.right);
      const y = value => scale(value, yMin, yMax, height - margin.bottom, margin.top);
      const ticks = xTickValues(xMetric, xMode)
        .map(value => ({{value, position: transformX(value, xMetric, xMode)}}))
        .filter(tick => tick.position >= xMin - 1e-9 && tick.position <= xMax + 1e-9);
      const yTicks = [0, 0.25, 0.5, 0.75, 1.0].includes(yMax) ? [0, 0.5, 1.0] : [0, yMax / 4, yMax / 2, yMax * 0.75, yMax];
      const point = row => {{
        const title = `${{row.system_name}}\\n${{row.description}}\\n${{xMetric}}: ${{fmt(row[xMetric])}}\\n${{yMetric}}: ${{fmt(row[yMetric])}}\\nx scale: ${{xMode}}`;
        return `<circle cx="${{x(transformX(row[xMetric], xMetric, xMode))}}" cy="${{y(row[yMetric])}}" r="${{row.group === "Oracle" ? 6 : 5}}" fill="${{colors[row.group] || colors.Other}}" opacity="0.9"><title>${{title}}</title></circle>`;
      }};
      const rawLinks = rows.filter(row => row.raw_feasible_utility !== null && row.raw_compliance_rate !== null && yMetric === "feasible_utility" && xMetric === "compliance_rate")
        .map(row => `<line x1="${{x(transformX(row.raw_compliance_rate, xMetric, xMode))}}" y1="${{y(row.raw_feasible_utility)}}" x2="${{x(transformX(row.compliance_rate, xMetric, xMode))}}" y2="${{y(row.feasible_utility)}}" stroke="#9aa5a1" stroke-width="1.5" opacity="0.55"><title>Raw-to-final shift: ${{row.system_name}}</title></line>`)
        .join("");
      const labels = byMetricDesc(yMetric).slice(0, 8).filter(row => row[xMetric] !== null && row[yMetric] !== null)
        .map(row => `<text x="${{x(transformX(row[xMetric], xMetric, xMode)) + 7}}" y="${{y(row[yMetric]) - 5}}" font-size="10" fill="#3b4650">${{row.base_system}}</text>`)
        .join("");
      document.getElementById("scatter").innerHTML = `
        <svg viewBox="0 0 ${{width}} ${{height}}" role="img" aria-label="Compliance utility frontier">
          <g class="axis">
            <line x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}"></line>
            <line x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}"></line>
            ${{ticks.map(tick => `<g><line x1="${{x(tick.position)}}" y1="${{height - margin.bottom}}" x2="${{x(tick.position)}}" y2="${{height - margin.bottom + 5}}"></line><text x="${{x(tick.position)}}" y="${{height - margin.bottom + 22}}" text-anchor="middle">${{xTickLabel(tick.value, xMode)}}</text></g>`).join("")}}
            ${{yTicks.map(tick => `<g><line x1="${{margin.left - 5}}" y1="${{y(tick)}}" x2="${{margin.left}}" y2="${{y(tick)}}"></line><text x="${{margin.left - 9}}" y="${{y(tick) + 4}}" text-anchor="end">${{fmt(tick)}}</text></g>`).join("")}}
            <text x="${{width / 2}}" y="${{height - 14}}" text-anchor="middle">${{xAxisLabel(xMetric, xMode)}}</text>
            <text transform="translate(18 ${{height / 2}}) rotate(-90)" text-anchor="middle">${{yMetric}}</text>
          </g>
          ${{rawLinks}}
          ${{data.map(point).join("")}}
          ${{labels}}
        </svg>`;
      document.getElementById("legend").innerHTML = Object.keys(colors).map(group => `<span><i class="swatch" style="background:${{colors[group]}}"></i>${{group}}</span>`).join("");
    }}

    function renderLeaderboard() {{
      const data = primaryRows().filter(row => row.feasible_utility !== null).sort((a, b) => b.feasible_utility - a.feasible_utility).slice(0, 16);
      const maxValue = Math.max(...data.map(row => row.feasible_utility), 1);
      document.getElementById("leaderboard").innerHTML = data.map(row => `
        <div class="bar-row" title="${{row.description}}">
          <div>
            <div class="bar-label">${{row.system_name}}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${{100 * row.feasible_utility / maxValue}}%; background:${{colors[row.group] || colors.Other}}"></div></div>
          </div>
          <div class="bar-value">${{fmt(row.feasible_utility)}}</div>
        </div>`).join("");
    }}

    function renderRepairBars() {{
      const data = rows
        .filter(row => row.raw_feasible_utility !== null && row.feasible_utility !== null)
        .map(row => ({{...row, delta: row.feasible_utility - row.raw_feasible_utility}}))
        .filter(row => Math.abs(row.delta) > 0.0001)
        .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
        .slice(0, 14);
      if (!data.length) {{
        document.getElementById("repairBars").innerHTML = "<p class='subtle'>No raw-to-final repair deltas were available.</p>";
        return;
      }}
      const maxAbs = Math.max(...data.map(row => Math.abs(row.delta)), 1);
      document.getElementById("repairBars").innerHTML = data.map(row => `
        <div class="bar-row" title="${{row.description}}">
          <div>
            <div class="bar-label">${{row.system_name}}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${{100 * Math.abs(row.delta) / maxAbs}}%; background:${{row.delta >= 0 ? "#7c3aed" : "#ca8a04"}}"></div></div>
          </div>
          <div class="bar-value">${{row.delta >= 0 ? "+" : ""}}${{fmt(row.delta)}}</div>
        </div>`).join("");
    }}

    function renderTable() {{
      const group = document.getElementById("groupFilter").value;
      const search = document.getElementById("searchBox").value.trim().toLowerCase();
      const filtered = rows.filter(row => {{
        const groupOk = group === "all" || row.group === group;
        const text = `${{row.system_name}} ${{row.display_name}} ${{row.provider}} ${{row.description}}`.toLowerCase();
        return groupOk && (!search || text.includes(search));
      }});
      document.getElementById("systemRows").innerHTML = filtered.map(row => `
        <tr>
          <td><code>${{row.system_name}}</code></td>
          <td><span class="pill ${{row.group}}">${{row.group}}</span></td>
          <td class="num">${{fmt(row.feasible_utility)}}</td>
          <td class="num">${{fmt(row.raw_feasible_utility)}}</td>
          <td class="num">${{fmt(row.ndcg_at_k)}}</td>
          <td class="num">${{fmt(row.compliance_rate)}}</td>
          <td class="num">${{fmt(row.raw_compliance_rate)}}</td>
          <td class="num">${{fmt(row.repaired_rate)}}</td>
          <td>${{row.description}}</td>
        </tr>`).join("");
    }}

    function renderMetricDefinitions() {{
      document.getElementById("metricDefinitions").innerHTML = Object.entries(metricHelp)
        .map(([metric, description]) => `<dt><code>${{metric}}</code></dt><dd>${{description}}</dd>`)
        .join("");
    }}

    document.getElementById("xMetric").addEventListener("change", renderScatter);
    document.getElementById("xScale").addEventListener("change", renderScatter);
    document.getElementById("yMetric").addEventListener("change", renderScatter);
    document.getElementById("groupFilter").addEventListener("change", renderTable);
    document.getElementById("searchBox").addEventListener("input", renderTable);
    renderSummary();
    renderScatter();
    renderLeaderboard();
    renderRepairBars();
    renderTable();
    renderMetricDefinitions();
  </script>
</body>
</html>
"""
    output.write_text(html, encoding="utf-8")
    return output


def _results_glossary() -> list[str]:
    return [
        "## Label and Metric Glossary",
        "",
        "### Study terms",
        "",
        "- CARA: public compound-activity benchmark used here as the source substrate for assay-level support/query tasks.",
        "- LO: lead optimisation. In this project, LO cards represent an observed support set plus candidate compounds to prioritise next.",
        "- VS: virtual screening. VS is not the primary run here; it usually means ranking a broader candidate set for activity.",
        "- Decision card: one benchmark instance containing support compounds, a candidate pool, hard constraints, budget `k`, and hidden activity values used only by the scorer.",
        "- Support set: already-tested compounds with measured activity that systems may learn from but must not recommend.",
        "- Candidate pool: compounds eligible for selection, subject to hard constraints.",
        "- QSAR: quantitative structure-activity relationship; here, conventional ML regressors trained on support-set Morgan fingerprints and measured activity, then used to rank feasible candidates by predicted activity.",
        "- Oracle: non-deployable upper-bound scorer that uses hidden activity values. It is a sanity check, not a real model.",
        "- Validator: deterministic harness logic that checks schema, candidate IDs, duplicates, support-set exclusion, and molecular constraints. It does not use hidden activity values.",
        "- Direct JSON: the current LLM prompt profile that asks for final JSON only, reducing failures where reasoning/prose consumes the visible output budget.",
        "",
        "### System labels",
        "",
        "- `oracle_valid_topk`: non-deployable upper-bound control that uses hidden candidate activity values to choose the best valid top-k set.",
        "- `random_valid`: random valid-candidate baseline.",
        "- `rules_only`: deterministic fallback/rule ranking after applying hard constraints.",
        "- `similarity_to_best_active`: ranks candidates by molecular similarity to the best active support compound.",
        "- `qsar_rf`: QSAR random forest regressor trained on support-set Morgan fingerprints.",
        "- `qsar_gbt`: QSAR gradient-boosting regressor trained on support-set Morgan fingerprints.",
        "- `qsar_svm`: QSAR sparse-scaled linear-kernel support-vector regressor trained on support-set Morgan fingerprints.",
        "- `bare_llm`: LLM receives the decision card and returns candidate IDs without deterministic repair.",
        "- `llm_tools`: LLM condition with extra computed descriptor/tool-summary fields in the candidate rows.",
        "- `llm_validator`: guarded LLM system; raw output is checked and invalid/missing slots may be deterministically repaired.",
        "- `llm_tools_validator`: tool-summary LLM condition plus deterministic checking and repair.",
        "- `*_frontier_selector`: legacy run label for the direct-JSON frontier interface. It means final-answer JSON prompting with no explicit high/extended-thinking mode where avoidable.",
        "- `*_frontier`: original frontier/high-reasoning or provider-default frontier condition.",
        "- `*_fast`: lower-latency/lower-cost provider condition.",
        "",
        "### Metrics",
        "",
        "- `feasible_utility`: sum of hidden activity values for selected candidates that satisfy all hard constraints. Higher is better.",
        "- `raw_feasible_utility`: feasible utility before deterministic validator repair. This is the closer measure of raw LLM behavior.",
        "- `ndcg_at_k`: ranking-quality score using hidden activity as graded relevance. Higher is better; `1.0` is ideal ranking.",
        "- `raw_ndcg_at_k`: NDCG before deterministic validator repair.",
        "- `constrained_regret`: oracle valid top-k utility minus observed feasible utility. Lower is better.",
        "- `compliance_rate`: fraction of the requested `k` selections that are valid after final repair, if repair applies.",
        "- `raw_compliance_rate`: compliance before deterministic validator repair.",
        "- `schema_error_rate`: fraction of cards with final schema/contract errors.",
        "- `raw_schema_error_rate`: schema/contract error rate before deterministic validator repair.",
        "- `repaired_from_empty_rate`: fraction of cards where the validator repaired an empty raw selection list. This should be near zero for a usable LLM interface.",
        "",
        "### Interpretation rules",
        "",
        "- Raw metrics describe model behavior; final metrics for `*_validator` rows describe model plus deterministic guardrail behavior.",
        "- Oracle controls are sanity checks, not systems that could be used prospectively.",
        "- A row can be highly compliant but still have weak utility; this distinction is the main object of the audit.",
    ]


def write_results_summary(comparison_csv: Path, out_dir: Path, *, title: str = "SpecGuard-Chem v2 Results Summary") -> Path:
    frame = pd.read_csv(comparison_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not frame.empty and "system_name" in frame.columns:
        frame = frame.sort_values(["feasible_utility", "compliance_rate"], ascending=[False, False])
        oracle = frame[frame["system_name"].map(_is_oracle_system)]
        primary = frame[~frame["system_name"].map(_is_oracle_system)]
    else:
        oracle = frame
        primary = frame

    columns = [
        "system_name",
        "feasible_utility",
        "raw_feasible_utility",
        "ndcg_at_k",
        "raw_ndcg_at_k",
        "constrained_regret",
        "compliance_rate",
        "raw_compliance_rate",
        "schema_error_rate",
        "raw_schema_error_rate",
        "repaired_from_empty_rate",
    ]
    generated_at = datetime.now(timezone.utc).isoformat()
    content = [
        f"# {title}",
        "",
        f"Generated at: `{generated_at}`",
        "",
        f"Source comparison CSV: `{comparison_csv}`",
        "",
        "This report is a computational audit artifact. It ranks provided candidate IDs only and does not claim synthesis feasibility, safety, selectivity, clinical utility, or therapeutic value.",
        "",
        "## Primary Systems",
        "",
        _markdown_table(primary, columns),
        "## Oracle Controls",
        "",
        _markdown_table(oracle, columns),
        "## Reading Guide",
        "",
        "- Higher feasible utility and NDCG@k are better.",
        "- Raw columns score the model output before deterministic validator repair.",
        "- Final columns score the selected output after validator repair where applicable.",
        "- Lower constrained regret and schema error rate are better.",
        "- Oracle controls are sanity checks and must not be mixed into primary system claims.",
        "",
        *_results_glossary(),
    ]
    output = out_dir / "RESULTS_SUMMARY.md"
    output.write_text("\n".join(content) + "\n", encoding="utf-8")
    return output
