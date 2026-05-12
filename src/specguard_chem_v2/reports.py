from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs

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


METRIC_EXAMPLES = {
    "feasible_utility": "Example: k=3 and the final valid selections have hidden activities 7.2, 6.8, and 0.0 for an invalid or missing slot. feasible_utility = 7.2 + 6.8 + 0.0 = 14.0.",
    "raw_feasible_utility": "Same calculation as feasible_utility, but applied to the model's raw output before deterministic validator repair.",
    "ndcg_at_k": "Example: the best possible valid ranking has DCG=18.0 and the system ranking has DCG=14.4. NDCG@k = 14.4 / 18.0 = 0.80.",
    "raw_ndcg_at_k": "Same NDCG@k calculation, but on the raw model output before validator repair.",
    "constrained_regret": "Example: the hidden-activity oracle can reach 90.0 feasible utility and a system reaches 76.0. constrained_regret = 90.0 - 76.0 = 14.0.",
    "compliance_rate": "Example: budget k=10 and 9 final selections are valid candidate IDs satisfying all hard constraints. compliance_rate = 9 / 10 = 0.90.",
    "raw_compliance_rate": "Same compliance calculation, but on the raw model output before validator repair.",
    "schema_error_rate": "Example: if a card has a malformed final output, wrong k, or missing candidate IDs, schema_error_rate=1 for that card; otherwise 0. Run summaries average this over cards.",
    "raw_schema_error_rate": "Same schema/contract error calculation, but before validator repair.",
    "repaired_rate": "Example: if validator repair changed 12 out of 50 raw card outputs, repaired_rate = 12 / 50 = 0.24.",
    "repaired_from_empty_rate": "Example: if 2 out of 50 cards had an empty raw selection list that was filled by repair, repaired_from_empty_rate = 2 / 50 = 0.04.",
}


def _attr(value: object) -> str:
    return escape(str(value), quote=True).replace("\n", "&#10;")


def _term(label: str, tooltip: str, *, example: str = "", title: str | None = None) -> str:
    title_attr = f' data-tooltip-title="{_attr(title)}"' if title else ""
    example_attr = f' data-example="{_attr(example)}"' if example else ""
    return (
        f'<span class="term" tabindex="0"{title_attr} '
        f'data-tooltip="{_attr(tooltip)}"{example_attr}>{escape(label)}</span>'
    )


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
    plotly_js = get_plotlyjs()
    run_pipeline_term = _term(
        "Run Pipeline",
        "The reproducible path from frozen decision cards to scored result artifacts.",
        example="cards.jsonl -> run traces.jsonl -> score summary.json -> comparison CSV -> dashboard/report",
    )
    decision_cards_term = _term(
        "1. Decision cards",
        "One benchmark instance: support compounds, candidate pool, hard constraints, budget k, and hidden scorer-only activity values.",
        example='{\n  "task_id": "CARA_LO_assay_0001",\n  "budget_k": 10,\n  "support_set": [{"id": "S001", "smiles": "...", "pIC50": 6.4}],\n  "candidate_pool": [{"id": "C017", "mw": 412.2, "clogp": 3.1}],\n  "hard_constraints": ["MW <= 500", "cLogP <= 4.5", "no support compounds"]\n}',
    )
    system_output_term = _term(
        "2. System output",
        "The runnable system returns an ordered batch of candidate IDs. Baselines produce this deterministically; LLM rows produce it from the prompt response.",
        example='{\n  "selections": [\n    {"rank": 1, "candidate_id": "C017", "confidence": 0.72},\n    {"rank": 2, "candidate_id": "C042", "confidence": 0.61}\n  ]\n}',
    )
    raw_audit_term = _term(
        "3. Raw audit",
        "Scores and records the model output before deterministic validator repair, so repaired behavior is not mistaken for raw model behavior.",
        example="raw_output: C017, C017, S003\nraw_issues: duplicate C017; support compound S003; fewer than k unique valid candidate IDs",
    )
    validator_term = _term(
        "4. Validator",
        "Deterministic harness logic for schema, candidate IDs, duplicates, support-set exclusion, and RDKit/property constraints. It does not use hidden activity.",
        example="kept: C017\nrejected: duplicate C017, support compound S003\nfilled missing slots from fallback_ranking(card)\nvalidator_repaired: true",
    )
    scoring_term = _term(
        "5. Scoring",
        "Computes utility, ranking quality, compliance, regret, repair rates, and comparison tables from the final output and raw output where available.",
        example="feasible_utility = sum(hidden activity for valid selected IDs)\ncompliance_rate = valid_selected_count / budget_k\nconstrained_regret = oracle_valid_topk_utility - feasible_utility",
    )
    table_terms = {
        "feasible_utility": _term(
            "Utility",
            METRIC_DESCRIPTIONS["feasible_utility"],
            example=METRIC_EXAMPLES["feasible_utility"],
            title="feasible_utility",
        ),
        "raw_feasible_utility": _term(
            "Raw utility",
            METRIC_DESCRIPTIONS["raw_feasible_utility"],
            example=METRIC_EXAMPLES["raw_feasible_utility"],
            title="raw_feasible_utility",
        ),
        "ndcg_at_k": _term(
            "NDCG",
            METRIC_DESCRIPTIONS["ndcg_at_k"],
            example=METRIC_EXAMPLES["ndcg_at_k"],
            title="ndcg_at_k",
        ),
        "compliance_rate": _term(
            "Compliance",
            METRIC_DESCRIPTIONS["compliance_rate"],
            example=METRIC_EXAMPLES["compliance_rate"],
            title="compliance_rate",
        ),
        "raw_compliance_rate": _term(
            "Raw compliance",
            METRIC_DESCRIPTIONS["raw_compliance_rate"],
            example=METRIC_EXAMPLES["raw_compliance_rate"],
            title="raw_compliance_rate",
        ),
        "repaired_rate": _term(
            "Repaired",
            METRIC_DESCRIPTIONS["repaired_rate"],
            example=METRIC_EXAMPLES["repaired_rate"],
            title="repaired_rate",
        ),
    }
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
    .hypothesis-grid {{ display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 12px; }}
    .hypothesis {{
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fbfcfa;
      padding: 12px;
    }}
    .hypothesis-title {{ display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 6px; }}
    .hypothesis-title strong {{ font-size: 14px; }}
    .status {{ border-radius: 999px; color: #fff; display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; white-space: nowrap; }}
    .status-supported {{ background: #0f766e; }}
    .status-partial {{ background: #a16207; }}
    .status-caveat {{ background: #475569; }}
    .evidence {{ color: var(--muted); margin: 0; }}
    .term {{
      border-bottom: 1px dotted var(--muted);
      cursor: help;
      text-decoration: none;
      position: relative;
    }}
    .rich-tooltip {{
      background: #17202a;
      border-radius: 6px;
      box-shadow: 0 8px 24px rgba(31, 41, 51, 0.22);
      color: #ffffff;
      display: none;
      font-size: 12px;
      font-weight: 500;
      line-height: 1.35;
      max-width: min(460px, calc(100vw - 24px));
      opacity: 0;
      padding: 10px 12px;
      pointer-events: none;
      position: fixed;
      text-transform: none;
      transform: translateY(-4px);
      transition: opacity 120ms ease, transform 120ms ease;
      white-space: normal;
      z-index: 1000;
    }}
    .rich-tooltip.visible {{
      display: block;
      opacity: 1;
      transform: translateY(0);
    }}
    .rich-tooltip-title {{
      color: #ffffff;
      font-weight: 800;
      margin-bottom: 4px;
    }}
    .rich-tooltip-body {{ color: #edf2f0; }}
    .rich-tooltip-example {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.16);
      border-radius: 5px;
      color: #f8fafc;
      font: 11px/1.4 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      margin: 8px 0 0;
      overflow-x: auto;
      padding: 8px;
      white-space: pre-wrap;
    }}
    .metric-chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 4px 0 12px;
    }}
    .metric-chip {{
      background: #edf0ec;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--ink);
      display: inline-flex;
      font-size: 12px;
      padding: 3px 8px;
    }}
    .chart {{ min-height: 420px; }}
    .side-chart {{ min-height: 520px; }}
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
      .summary-grid, .plot-grid, .flow, .hypothesis-grid {{ grid-template-columns: 1fr; }}
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
      <h2>{run_pipeline_term}</h2>
      <div class="flow">
        <div class="flow-step"><strong>{decision_cards_term}</strong><small>Support set, candidate pool, hard constraints, and budget k.</small></div>
        <div class="flow-step"><strong>{system_output_term}</strong><small>Baselines or LLMs return ranked candidate IDs.</small></div>
        <div class="flow-step"><strong>{raw_audit_term}</strong><small>Raw LLM selections are scored before repair where available.</small></div>
        <div class="flow-step"><strong>{validator_term}</strong><small>Deterministic schema, ID, duplicate, support-exclusion, and RDKit/property checks.</small></div>
        <div class="flow-step"><strong>{scoring_term}</strong><small>Utility, compliance, regret, repair rate, and frontier plots.</small></div>
      </div>
    </section>

    <section class="panel" style="margin-top:16px">
      <h2>Original Hypotheses and Evidence</h2>
      <p class="subtle">This panel links the completed comparison table back to the project brief. It is descriptive, not a replacement for statistical analysis in the manuscript.</p>
      <div id="hypotheses" class="hypothesis-grid"></div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px">
      <div class="panel">
        <h2><span class="term" tabindex="0" data-tooltip="Scatter plot separating specification compliance on the x-axis from medicinal-chemistry decision utility on the y-axis.">Compliance-Utility Frontier</span></h2>
        <div class="controls">
          <label>{_term("Y metric", "Metric plotted on the vertical axis. Hover the selected metric chip below for the calculation.")}
            <select id="yMetric">
              <option value="feasible_utility">Final feasible utility</option>
              <option value="raw_feasible_utility">Raw feasible utility</option>
              <option value="ndcg_at_k">Final NDCG@k</option>
              <option value="raw_ndcg_at_k">Raw NDCG@k</option>
            </select>
          </label>
          <label>{_term("X metric", "Metric plotted on the horizontal axis. Hover the selected metric chip below for the calculation.")}
            <select id="xMetric">
              <option value="compliance_rate">Final compliance</option>
              <option value="raw_compliance_rate">Raw compliance</option>
              <option value="schema_error_rate">Final schema error</option>
              <option value="raw_schema_error_rate">Raw schema error</option>
            </select>
          </label>
          <label>{_term("X scale", "How the x-axis is transformed. Log gap to 1.0 expands values clustered near perfect compliance; log value expands small error rates.")}
            <select id="xScale">
              <option value="auto" selected>Auto log for clustered rates</option>
              <option value="linear">Linear</option>
              <option value="log_gap">Log gap to 1.0</option>
              <option value="log_value">Log value</option>
            </select>
          </label>
          <label>
            <span class="term" tabindex="0" data-tooltip="Switches the LLM scatter points between final scored outputs, raw model outputs, or both connected by repair links. Deterministic baselines remain shown as context.">LLM point view</span>
            <select id="repairPointView">
              <option value="final" selected>Final scored points</option>
              <option value="raw">Raw LLM points</option>
              <option value="both">Raw + final repair links</option>
            </select>
          </label>
        </div>
        <div class="metric-chip-row" id="selectedMetricDefinitions"></div>
        <p class="subtle" id="repairLinkNote">Showing final scored outputs. For validator rows, final points may include deterministic repair.</p>
        <div id="scatter" class="chart"></div>
        <div class="legend" id="legend"></div>
      </div>
      <div class="panel">
        <h2>Top <span class="term" tabindex="0" data-tooltip="Primary systems exclude oracle controls. They are the deployable or prospectively runnable systems used for main comparisons.">Primary Systems</span></h2>
        <div id="leaderboard" class="side-chart"></div>
      </div>
    </section>

    <section class="grid plot-grid" style="margin-top:16px">
      <div class="panel">
        <h2>Raw-to-Final Repair Delta</h2>
        <p class="subtle">Positive bars mean deterministic repair increased final feasible utility relative to raw model output.</p>
        <div id="repairBars" class="chart"></div>
      </div>
      <div class="panel">
        <h2>Label Guide</h2>
        <p><strong><span class="term" tabindex="0" data-tooltip="Quantitative structure-activity relationship models: conventional molecular ML regressors, not language models.">QSAR models:</span></strong> all three train on support-set Morgan fingerprints and measured activity, then rank feasible candidates by predicted activity.</p>
        <p><code>qsar_rf</code> is a random forest regressor; <code>qsar_gbt</code> is a gradient-boosting regressor; <code>qsar_svm</code> is a sparse-scaled linear-kernel support-vector regressor.</p>
        <p><strong><span class="term" tabindex="0" data-tooltip="Deterministic harness logic, not a model and not an activity oracle.">Validator:</span></strong> deterministic harness checks and repair. It does not inspect hidden activity values.</p>
        <p><strong><span class="term" tabindex="0" data-tooltip="A non-deployable control that uses hidden candidate activity values.">Oracle:</span></strong> hidden-activity upper bound used only to show remaining decision headroom.</p>
        <p><strong><span class="term" tabindex="0" data-tooltip="The current prompt profile: final answer JSON only, without relying on visible chain-of-thought text.">Direct JSON:</span></strong> final-answer JSON prompting designed to avoid visible-output budget failures.</p>
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
              <th>{table_terms["feasible_utility"]}</th>
              <th>{table_terms["raw_feasible_utility"]}</th>
              <th>{table_terms["ndcg_at_k"]}</th>
              <th>{table_terms["compliance_rate"]}</th>
              <th>{table_terms["raw_compliance_rate"]}</th>
              <th>{table_terms["repaired_rate"]}</th>
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
    <div id="richTooltip" class="rich-tooltip" role="tooltip" aria-hidden="true"></div>
  </main>
  <script>
{plotly_js}
  </script>
  <script>
    const rows = {_json_for_html(rows)};
    const metricHelp = {_json_for_html(METRIC_DESCRIPTIONS)};
    const metricExamples = {_json_for_html(METRIC_EXAMPLES)};
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
        [metricTerm("feasible_utility", "Best primary utility"), primary ? fmt(primary.feasible_utility) : "", primary ? escapeHtml(primary.system_name) : ""],
        [metricTerm("feasible_utility", "Oracle utility"), oracle ? fmt(oracle.feasible_utility) : "", "Upper bound, not deployable"],
        [metricTerm("raw_feasible_utility", "Best raw LLM utility"), rawLlm ? fmt(rawLlm.raw_feasible_utility) : "", rawLlm ? escapeHtml(rawLlm.system_name) : ""],
        [metricTerm("repaired_rate", "Repair-sensitive rows"), String(repairSensitive), "Rows with repaired_rate >= 0.10"]
      ];
      document.getElementById("summaryCards").innerHTML = cards.map(card => `
        <div class="panel">
          <div class="stat-label">${{card[0]}}</div>
          <div class="stat-value">${{card[1]}}</div>
          <div class="stat-note">${{card[2]}}</div>
        </div>`).join("");
    }}

    function rowByName(name) {{
      return rows.find(row => row.system_name === name) || null;
    }}

    function bestRow(metric, filterFn = () => true) {{
      return rows
        .filter(row => filterFn(row) && row[metric] !== null)
        .sort((a, b) => b[metric] - a[metric])[0] || null;
    }}

    function metricRange(metric, filterFn = () => true) {{
      const values = rows.filter(row => filterFn(row) && row[metric] !== null).map(row => row[metric]);
      if (!values.length) return null;
      return {{min: Math.min(...values), max: Math.max(...values)}};
    }}

    function renderHypotheses() {{
      const bestQsar = bestRow("feasible_utility", row => row.group === "QSAR");
      const bestLlmFinal = bestRow("feasible_utility", row => row.group === "LLM");
      const bestRawLlm = bestRow("raw_feasible_utility", row => row.group === "LLM");
      const similarity = rowByName("similarity_to_best_active");
      const bareOpenai = rowByName("bare_llm__openai_frontier_selector");
      const toolsOpenai = rowByName("llm_tools__openai_frontier_selector");
      const validatorOpenai = rowByName("llm_validator__openai_frontier_selector");
      const repairRows = rows
        .filter(row => row.raw_feasible_utility !== null && row.feasible_utility !== null)
        .map(row => ({{...row, delta: row.feasible_utility - row.raw_feasible_utility}}))
        .sort((a, b) => b.delta - a.delta);
      const biggestRepair = repairRows[0];
      const perfectComplianceRange = metricRange("feasible_utility", row => row.group !== "Oracle" && row.compliance_rate !== null && row.compliance_rate >= 0.999);
      const hypotheses = [
        {{
          label: "H1",
          status: "Supported",
          statusClass: "status-supported",
          title: "Validators raise compliance more reliably than utility.",
          evidence: biggestRepair
            ? `Largest observed raw-to-final ${{metricTerm("feasible_utility", "utility")}} shift is ${{escapeHtml(biggestRepair.system_name)}}: +${{fmt(biggestRepair.delta)}} feasible utility, with ${{metricTerm("repaired_rate", "repaired_rate")}} ${{fmt(biggestRepair.repaired_rate)}}. These final scores are guarded-system behavior, not raw model behavior.`
            : "Raw-to-final repair data were not available for this table."
        }},
        {{
          label: "H2",
          status: "Supported",
          statusClass: "status-supported",
          title: "Simple QSAR and similarity baselines are competitive.",
          evidence: `Best QSAR is ${{escapeHtml(bestQsar?.system_name || "n/a")}} at ${{fmt(bestQsar?.feasible_utility)}} ${{metricTerm("feasible_utility", "feasible utility")}}; best LLM final is ${{escapeHtml(bestLlmFinal?.system_name || "n/a")}} at ${{fmt(bestLlmFinal?.feasible_utility)}}; similarity-to-best-active is ${{fmt(similarity?.feasible_utility)}}.`
        }},
        {{
          label: "H3",
          status: "Partial",
          statusClass: "status-partial",
          title: "The best LLM system is likely hybrid, not a naked LLM.",
          evidence: `For OpenAI direct JSON, bare LLM is ${{fmt(bareOpenai?.feasible_utility)}}, tools-only is ${{fmt(toolsOpenai?.feasible_utility)}}, and validator-assisted is ${{fmt(validatorOpenai?.feasible_utility)}} on ${{metricTerm("feasible_utility", "feasible utility")}}. Hybrid/guarded LLM rows improve on bare LLMs, but none beats the best QSAR baseline.`
        }},
        {{
          label: "H4",
          status: "Supported",
          statusClass: "status-supported",
          title: "Compliance and utility are imperfectly correlated.",
          evidence: perfectComplianceRange
            ? `Among non-oracle rows with final ${{metricTerm("compliance_rate", "compliance")}} near 1.0, ${{metricTerm("feasible_utility", "feasible utility")}} ranges from ${{fmt(perfectComplianceRange.min)}} to ${{fmt(perfectComplianceRange.max)}}. Perfect compliance alone does not imply strong prioritisation utility.`
            : "No near-perfect compliance rows were available."
        }},
        {{
          label: "Central contention",
          status: "Caveat",
          statusClass: "status-caveat",
          title: "Compliance is not utility.",
          evidence: `The current results support the audit framing: direct-JSON LLMs can become valid and useful, but best raw LLM ${{metricTerm("raw_feasible_utility", "utility")}} (${{fmt(bestRawLlm?.raw_feasible_utility)}}) remains below best QSAR ${{metricTerm("feasible_utility", "utility")}} (${{fmt(bestQsar?.feasible_utility)}}), and validator repair can materially change final scores.`
        }}
      ];
      document.getElementById("hypotheses").innerHTML = hypotheses.map(item => `
        <article class="hypothesis">
          <div class="hypothesis-title">
            <strong>${{item.label}}: ${{item.title}}</strong>
            <span class="status ${{item.statusClass}}">${{item.status}}</span>
          </div>
          <p class="evidence">${{item.evidence}}</p>
        </article>`).join("");
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
      if (mode === "log_gap") return [0, 0.9, 0.99, 0.999, 1.0];
      if (mode === "log_value") return [0, 0.001, 0.01, 0.1, 1.0];
      return [0, 0.25, 0.5, 0.75, 1.0];
    }}

    function xTickLabel(value, mode) {{
      if (mode === "log_gap") return value === 1 ? "1.000" : fmt(value, value >= 0.99 ? 3 : 2);
      if (mode === "log_value") return value === 0 ? "0" : String(value);
      return fmt(value, 2);
    }}

    function xAxisLabel(metric, mode) {{
      if (mode === "log_gap") return `${{metric}}<br>(log distance from 1.0; right is better)`;
      if (mode === "log_value") return `${{metric}} (log value)`;
      return metric;
    }}

    function rawMetricFor(metric) {{
      const mapping = {{
        feasible_utility: "raw_feasible_utility",
        ndcg_at_k: "raw_ndcg_at_k",
        compliance_rate: "raw_compliance_rate",
        schema_error_rate: "raw_schema_error_rate"
      }};
      return mapping[metric] || metric;
    }}

    function renderSelectedMetricDefinitions() {{
      const xMetric = document.getElementById("xMetric").value;
      const yMetric = document.getElementById("yMetric").value;
      const xMode = effectiveXScale(xMetric, document.getElementById("xScale").value);
      const chips = [
        `<span class="metric-chip">Y: ${{metricCodeTerm(yMetric)}}</span>`,
        `<span class="metric-chip">X: ${{metricCodeTerm(xMetric)}}</span>`,
        `<span class="metric-chip">${{termHtml("scale: " + xMode, "The selected x-axis transform. log_gap plots -log10(1 - value), which spreads values clustered close to 1.0. log_value plots log10(value), which spreads small error rates.", "linear: value is unchanged\\nlog_gap: compliance 0.99 becomes 2.0 because -log10(0.01)=2\\nlog_value: schema error 0.01 becomes -2.0 because log10(0.01)=-2")}}</span>`,
      ];
      document.getElementById("selectedMetricDefinitions").innerHTML = chips.join("");
    }}

    function hasRawPoint(row, rawXMetric, rawYMetric) {{
      return row[rawXMetric] !== null && row[rawXMetric] !== undefined && row[rawYMetric] !== null && row[rawYMetric] !== undefined;
    }}

    function wrapPlotLabel(value, maxLineLength = 24) {{
      const text = String(value);
      const chunks = text.split("__");
      const lines = [];
      let current = "";
      for (const chunk of chunks) {{
        const part = current ? "__" + chunk : chunk;
        if (current && current.length + part.length > maxLineLength) {{
          lines.push(current);
          current = chunk;
        }} else {{
          current += part;
        }}
      }}
      if (current) lines.push(current);
      const expanded = [];
      for (const line of lines) {{
        if (line.length <= maxLineLength + 8) {{
          expanded.push(line);
          continue;
        }}
        const pieces = line.split("_");
        let subline = "";
        for (const piece of pieces) {{
          const part = subline ? "_" + piece : piece;
          if (subline && subline.length + part.length > maxLineLength) {{
            expanded.push(subline);
            subline = piece;
          }} else {{
            subline += part;
          }}
        }}
        if (subline) expanded.push(subline);
      }}
      return expanded.join("<br>");
    }}

    function escapeHtml(value) {{
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function escapeAttr(value) {{
      return escapeHtml(value).replace(/\\n/g, "&#10;");
    }}

    function termHtml(label, tooltip, example = "", title = "") {{
      const titleAttr = title ? ` data-tooltip-title="${{escapeAttr(title)}}"` : "";
      const exampleAttr = example ? ` data-example="${{escapeAttr(example)}}"` : "";
      return `<span class="term" tabindex="0"${{titleAttr}} data-tooltip="${{escapeAttr(tooltip)}}"${{exampleAttr}}>${{escapeHtml(label)}}</span>`;
    }}

    function metricTerm(metric, label) {{
      return termHtml(label, metricHelp[metric] || metric, metricExamples[metric] || "", metric);
    }}

    function metricCodeTerm(metric) {{
      const tooltip = metricHelp[metric] || metric;
      const example = metricExamples[metric] || "";
      return `<code class="term" tabindex="0" data-tooltip-title="${{escapeAttr(metric)}}" data-tooltip="${{escapeAttr(tooltip)}}" data-example="${{escapeAttr(example)}}">${{escapeHtml(metric)}}</code>`;
    }}

    function wrapHoverText(value, maxLineLength = 68) {{
      const words = String(value || "").trim().split(/\\s+/).filter(Boolean);
      const lines = [];
      let current = "";
      for (const word of words) {{
        if (!current) {{
          current = word;
        }} else if (current.length + 1 + word.length > maxLineLength) {{
          lines.push(current);
          current = word;
        }} else {{
          current += " " + word;
        }}
      }}
      if (current) lines.push(current);
      return lines.map(escapeHtml).join("<br>");
    }}

    function wrapIdentifier(value, maxLineLength = 44) {{
      return wrapPlotLabel(value, maxLineLength).split("<br>").map(escapeHtml).join("<br>");
    }}

    function plotlyLayout(title, xTitle, yTitle, height = 460) {{
      return {{
        title: {{text: title, font: {{size: 15}}, x: 0}},
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "#fbfcfa",
        margin: {{l: 72, r: 24, t: 42, b: 68}},
        height,
        hovermode: "closest",
        hoverlabel: {{align: "left"}},
        legend: {{orientation: "h", y: -0.22}},
        font: {{family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", color: "#1f2933"}},
        xaxis: {{title: xTitle, gridcolor: "#e4e8e4", zerolinecolor: "#cbd5d0", automargin: true}},
        yaxis: {{title: yTitle, gridcolor: "#e4e8e4", zerolinecolor: "#cbd5d0", automargin: true}}
      }};
    }}

    const plotlyConfig = {{responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"]}};

    function renderScatter() {{
      const xMetric = document.getElementById("xMetric").value;
      const yMetric = document.getElementById("yMetric").value;
      const xMode = effectiveXScale(xMetric, document.getElementById("xScale").value);
      renderSelectedMetricDefinitions();
      const pointView = document.getElementById("repairPointView").value;
      const rawXMetric = rawMetricFor(xMetric);
      const rawYMetric = rawMetricFor(yMetric);
      const canShowRepair = rawXMetric !== xMetric || rawYMetric !== yMetric;
      const data = rows
        .map(row => {{
          const showRaw = pointView === "raw" && row.group === "LLM" && hasRawPoint(row, rawXMetric, rawYMetric);
          return {{
            ...row,
            plot_x: showRaw ? row[rawXMetric] : row[xMetric],
            plot_y: showRaw ? row[rawYMetric] : row[yMetric],
            point_kind: showRaw ? "raw LLM output" : "final scored output",
            marker_symbol: showRaw ? "circle-open" : "circle"
          }};
        }})
        .filter(row => row.plot_x !== null && row.plot_x !== undefined && row.plot_y !== null && row.plot_y !== undefined)
        .filter(row => pointView !== "raw" || row.group !== "LLM" || row.point_kind === "raw LLM output");
      const traces = [];
      const linkRows = rows.filter(row => hasRawPoint(row, rawXMetric, rawYMetric) && row[xMetric] !== null && row[xMetric] !== undefined && row[yMetric] !== null && row[yMetric] !== undefined);
      if (pointView === "both" && canShowRepair) {{
        linkRows.forEach((row, index) => traces.push({{
            type: "scatter",
            mode: "lines",
            name: "raw -> final repair",
            legendgroup: "repair_links",
            showlegend: index === 0,
            hoverinfo: "text",
            line: {{color: "#9aa5a1", width: 1.4, dash: "dot"}},
            opacity: 0.55,
            x: [transformX(row[rawXMetric], xMetric, xMode), transformX(row[xMetric], xMetric, xMode)],
            y: [row[rawYMetric], row[yMetric]],
            text: [`<b>${{wrapIdentifier(row.system_name)}}</b><br>raw ${{escapeHtml(xMetric)}}: ${{fmt(row[rawXMetric])}}<br>raw ${{escapeHtml(yMetric)}}: ${{fmt(row[rawYMetric])}}`, `<b>${{wrapIdentifier(row.system_name)}}</b><br>final ${{escapeHtml(xMetric)}}: ${{fmt(row[xMetric])}}<br>final ${{escapeHtml(yMetric)}}: ${{fmt(row[yMetric])}}`]
        }}));
        traces.push({{
          type: "scatter",
          mode: "markers",
          name: "raw output",
          legendgroup: "repair_links",
          x: linkRows.map(row => transformX(row[rawXMetric], xMetric, xMode)),
          y: linkRows.map(row => row[rawYMetric]),
          customdata: linkRows.map(row => [wrapIdentifier(row.system_name), row[rawXMetric], row[rawYMetric], row[xMetric], row[yMetric]]),
          hovertemplate: "<b>%{{customdata[0]}}</b><br>raw output<br>raw x: %{{customdata[1]:.3f}}<br>raw y: %{{customdata[2]:.3f}}<br>final x: %{{customdata[3]:.3f}}<br>final y: %{{customdata[4]:.3f}}<extra></extra>",
          marker: {{symbol: "circle-open", size: 11, color: "#64717f", line: {{color: "#64717f", width: 2}}}}
        }});
      }}
      for (const group of ["Oracle", "QSAR", "Baseline", "LLM", "Other"]) {{
        const groupRows = data.filter(row => row.group === group);
        if (!groupRows.length) continue;
        traces.push({{
          type: "scatter",
          mode: "markers",
          name: group,
          x: groupRows.map(row => transformX(row.plot_x, xMetric, xMode)),
          y: groupRows.map(row => row.plot_y),
          customdata: groupRows.map(row => [wrapIdentifier(row.system_name), wrapHoverText(row.description), row.plot_x, row.plot_y, wrapIdentifier(row.condition || "none"), row.point_kind]),
          hovertemplate: "<b>%{{customdata[0]}}</b><br>%{{customdata[5]}}<br>%{{customdata[1]}}<br>" + xMetric + ": %{{customdata[2]:.3f}}<br>" + yMetric + ": %{{customdata[3]:.3f}}<br>condition: %{{customdata[4]}}<extra></extra>",
          marker: {{size: group === "Oracle" ? 15 : 11, color: colors[group] || colors.Other, symbol: groupRows.map(row => row.marker_symbol), opacity: 0.88, line: {{color: "#ffffff", width: 1}}}}
        }});
      }}
      const tickValues = xTickValues(xMetric, xMode);
      const layout = plotlyLayout("Compliance versus utility", xAxisLabel(xMetric, xMode), yMetric, 500);
      layout.xaxis.tickmode = "array";
      layout.xaxis.tickvals = tickValues.map(value => transformX(value, xMetric, xMode));
      layout.xaxis.ticktext = tickValues.map(value => xTickLabel(value, xMode));
      Plotly.react("scatter", traces, layout, plotlyConfig);
      const note = document.getElementById("repairLinkNote");
      if (pointView === "raw") {{
        note.textContent = "Showing raw LLM output points where raw metrics are available; LLM rows without raw metrics are omitted, while deterministic baselines and oracle controls remain as context.";
      }} else if (pointView === "both" && canShowRepair) {{
        note.textContent = "Open grey circles are raw LLM outputs. Dotted grey segments connect each raw point to that same system's final scored point.";
      }} else if (pointView === "both") {{
        note.textContent = "Raw-to-final repair links require a final metric with a matching raw metric. Use final utility/compliance or final NDCG/compliance to inspect repair movement.";
      }} else {{
        note.textContent = "Showing final scored outputs. For validator rows, final points may include deterministic repair.";
      }}
      document.getElementById("legend").innerHTML = "";
    }}

    function renderLeaderboard() {{
      const data = primaryRows().filter(row => row.feasible_utility !== null).sort((a, b) => b.feasible_utility - a.feasible_utility).slice(0, 16);
      const plotRows = [...data].reverse();
      const trace = {{
        type: "bar",
        orientation: "h",
        x: plotRows.map(row => row.feasible_utility),
        y: plotRows.map(row => row.system_name),
        marker: {{color: plotRows.map(row => colors[row.group] || colors.Other)}},
        customdata: plotRows.map(row => [wrapHoverText(row.description), row.ndcg_at_k, row.compliance_rate, wrapIdentifier(row.system_name)]),
        hovertemplate: "<b>%{{customdata[3]}}</b><br>%{{customdata[0]}}<br>utility: %{{x:.3f}}<br>NDCG@k: %{{customdata[1]:.3f}}<br>compliance: %{{customdata[2]:.3f}}<extra></extra>"
      }};
      const layout = plotlyLayout("Primary-system leaderboard", "feasible_utility", "", 560);
      layout.margin = {{l: 138, r: 24, t: 42, b: 52}};
      layout.showlegend = false;
      layout.yaxis.tickmode = "array";
      layout.yaxis.tickvals = plotRows.map(row => row.system_name);
      layout.yaxis.ticktext = plotRows.map(row => wrapPlotLabel(row.system_name, 22));
      layout.yaxis.tickfont = {{size: 11}};
      Plotly.react("leaderboard", [trace], layout, plotlyConfig);
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
      const plotRows = [...data].reverse();
      const trace = {{
        type: "bar",
        orientation: "h",
        x: plotRows.map(row => row.delta),
        y: plotRows.map(row => row.system_name),
        marker: {{color: plotRows.map(row => row.delta >= 0 ? "#7c3aed" : "#ca8a04")}},
        customdata: plotRows.map(row => [row.raw_feasible_utility, row.feasible_utility, row.repaired_rate, wrapHoverText(row.description), wrapIdentifier(row.system_name)]),
        hovertemplate: "<b>%{{customdata[4]}}</b><br>%{{customdata[3]}}<br>raw utility: %{{customdata[0]:.3f}}<br>final utility: %{{customdata[1]:.3f}}<br>delta: %{{x:+.3f}}<br>repaired rate: %{{customdata[2]:.3f}}<extra></extra>"
      }};
      const layout = plotlyLayout("Validator repair effect", "final - raw feasible utility", "", 500);
      layout.margin = {{l: 138, r: 24, t: 42, b: 52}};
      layout.showlegend = false;
      layout.yaxis.tickmode = "array";
      layout.yaxis.tickvals = plotRows.map(row => row.system_name);
      layout.yaxis.ticktext = plotRows.map(row => wrapPlotLabel(row.system_name, 22));
      layout.yaxis.tickfont = {{size: 11}};
      layout.xaxis.zeroline = true;
      layout.xaxis.zerolinewidth = 2;
      layout.xaxis.zerolinecolor = "#64717f";
      Plotly.react("repairBars", [trace], layout, plotlyConfig);
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
        .map(([metric, description]) => `<dt>${{metricCodeTerm(metric)}}</dt><dd>${{escapeHtml(description)}}</dd>`)
        .join("");
    }}

    function tooltipElement() {{
      return document.getElementById("richTooltip");
    }}

    function showRichTooltip(term) {{
      const tooltip = tooltipElement();
      const title = term.dataset.tooltipTitle || term.textContent.trim();
      const body = term.dataset.tooltip || "";
      const example = term.dataset.example || "";
      tooltip.replaceChildren();
      const titleEl = document.createElement("div");
      titleEl.className = "rich-tooltip-title";
      titleEl.textContent = title;
      tooltip.appendChild(titleEl);
      if (body) {{
        const bodyEl = document.createElement("div");
        bodyEl.className = "rich-tooltip-body";
        bodyEl.textContent = body;
        tooltip.appendChild(bodyEl);
      }}
      if (example) {{
        const exampleEl = document.createElement("pre");
        exampleEl.className = "rich-tooltip-example";
        exampleEl.textContent = example;
        tooltip.appendChild(exampleEl);
      }}
      tooltip.style.display = "block";
      tooltip.setAttribute("aria-hidden", "false");
      const rect = term.getBoundingClientRect();
      const width = tooltip.offsetWidth;
      const height = tooltip.offsetHeight;
      const margin = 12;
      let left = Math.min(Math.max(margin, rect.left), window.innerWidth - width - margin);
      let top = rect.bottom + 8;
      if (top + height + margin > window.innerHeight) {{
        top = Math.max(margin, rect.top - height - 8);
      }}
      tooltip.style.left = `${{left}}px`;
      tooltip.style.top = `${{top}}px`;
      tooltip.classList.add("visible");
    }}

    function hideRichTooltip() {{
      const tooltip = tooltipElement();
      tooltip.classList.remove("visible");
      tooltip.setAttribute("aria-hidden", "true");
      tooltip.style.display = "none";
    }}

    function closestTerm(target) {{
      return target instanceof Element ? target.closest(".term") : null;
    }}

    document.addEventListener("mouseover", event => {{
      const term = closestTerm(event.target);
      if (term) showRichTooltip(term);
    }});
    document.addEventListener("mouseout", event => {{
      const term = closestTerm(event.target);
      if (term && (!event.relatedTarget || !term.contains(event.relatedTarget))) hideRichTooltip();
    }});
    document.addEventListener("focusin", event => {{
      const term = closestTerm(event.target);
      if (term) showRichTooltip(term);
    }});
    document.addEventListener("focusout", event => {{
      const term = closestTerm(event.target);
      if (term) hideRichTooltip();
    }});
    window.addEventListener("scroll", hideRichTooltip, true);
    window.addEventListener("resize", hideRichTooltip);

    document.getElementById("xMetric").addEventListener("change", renderScatter);
    document.getElementById("xScale").addEventListener("change", renderScatter);
    document.getElementById("yMetric").addEventListener("change", renderScatter);
    document.getElementById("repairPointView").addEventListener("change", renderScatter);
    document.getElementById("groupFilter").addEventListener("change", renderTable);
    document.getElementById("searchBox").addEventListener("input", renderTable);
    renderSummary();
    renderHypotheses();
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
