from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "paper/manuscript/generate_results.py"


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("manuscript_results_generator", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _metric_summary(
    system_name: str,
    interface: str,
    condition: str,
    *,
    utility: float,
    repaired: bool,
    repaired_rate: float = 0.0,
    source_sha256: str | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "system_name": system_name,
        "base_system_name": interface,
        "llm_model_config_id": condition,
        "num_cards": 91,
        "feasible_utility": utility,
        "ndcg_at_k": 0.8,
        "constrained_regret": 5.0,
        "action_validity": 1.0 if repaired else 0.9,
        "raw_feasible_utility": utility - (0.5 if repaired else 0.0),
        "raw_ndcg_at_k": 0.79,
        "raw_action_validity": 0.9,
        "repaired_rate": repaired_rate if repaired else 0.0,
        "actual_cost_usd": 1.0,
        "cost_coverage": 1.0,
    }
    if repaired:
        summary.update(
            {
                "repair_mode": "posthoc",
                "repair_source_system_name": system_name.removesuffix("__posthoc_repair"),
                "repair_source_trace_sha256": source_sha256,
            }
        )
    return summary


def _write_minimal_baselines(repo_root: Path, generator: ModuleType) -> None:
    comparison_rows = []
    for index, name in enumerate(generator.BASELINE_ORDER):
        row = {
            "system_name": name,
            "num_cards": 91,
            "feasible_utility": 60.0 + index,
            "feasible_utility_ci_low": 59.0 + index,
            "feasible_utility_ci_high": 61.0 + index,
            "ndcg_at_k": 0.8,
            "constrained_regret": 5.0,
            "action_validity": 1.0,
            "compliance_rate": 1.0,
            "valid_selected_count": 10,
        }
        comparison_rows.append(row)
        _write_json(
            repo_root / "release/v0.1.0/experiments/baselines" / name / "scores/summary.json",
            row,
        )
    _write_json(
        repo_root / "release/v0.1.0/experiments/baselines/comparison/system_comparison.json",
        comparison_rows,
    )


def _output_payload(
    task_id: str,
    system_name: str,
    candidate_ids: list[str],
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "system_name": system_name,
        "selections": [
            {"rank": rank, "candidate_id": candidate_id}
            for rank, candidate_id in enumerate(candidate_ids, start=1)
        ],
        "metadata": {},
    }


def _write_complete_llm_evidence(repo_root: Path, generator: ModuleType) -> dict[str, Path]:
    task_ids = [f"frozen_task_{index:03d}" for index in range(1, 92)]
    _write_jsonl(
        repo_root / "data/releases/v0.1.0/system_input_cards.jsonl",
        [{"task_id": task_id} for task_id in task_ids],
    )

    matrix_root = repo_root / "release/v0.1.0/experiments/llm/matrix"
    comparison_root = repo_root / "release/v0.1.0/experiments/llm/comparison"
    comparison_rows: list[dict[str, Any]] = []
    manifest_runs: list[dict[str, str]] = []
    raw_trace_paths: dict[str, Path] = {}
    all_pair_rows: list[dict[str, Any]] = []

    utility = 70.0
    for condition in generator.PRIMARY_LLM_CONDITIONS:
        provider_id = generator.CONDITION_PROVIDERS[condition][0]
        for interface in generator.PRIMARY_LLM_INTERFACES:
            raw_name = generator._raw_llm_name(interface, condition)
            repaired_name = generator._repaired_llm_name(interface, condition)
            run_root = matrix_root / condition / interface
            raw_trace_path = run_root / "trace.jsonl"
            raw_trace_paths[raw_name] = raw_trace_path
            raw_metadata = {
                "base_system_name": interface,
                "llm_model_config_id": condition,
                "llm_provider": provider_id,
            }
            raw_trace: list[dict[str, Any]] = []
            for index, task_id in enumerate(task_ids, start=1):
                raw_ids = [] if index == 1 else [f"{task_id}_raw_{rank}" for rank in range(1, 11)]
                raw_output = _output_payload(task_id, raw_name, raw_ids)
                raw_trace.append(
                    {
                        "task_id": task_id,
                        "system_name": raw_name,
                        "metadata": raw_metadata,
                        "output": raw_output,
                        "raw_output": raw_output,
                        "issues": [],
                        "raw_issues": (
                            [{"code": "wrong_k", "message": "missing selections"}]
                            if index == 1
                            else [{"code": "schema_missing_task_id", "message": "missing"}]
                            if index == 2
                            else []
                        ),
                        "repaired": False,
                    }
                )
            raw_scores = [
                {"task_id": task_id, "system_name": raw_name, "metadata": raw_metadata}
                for task_id in task_ids
            ]
            _write_jsonl(raw_trace_path, raw_trace)
            _write_jsonl(run_root / "scores/card_scores.jsonl", raw_scores)
            raw_summary = _metric_summary(
                raw_name,
                interface,
                condition,
                utility=utility,
                repaired=False,
            )
            _write_json(run_root / "scores/summary.json", raw_summary)
            comparison_rows.append(
                {**raw_summary, "system_group": "LLM", "display_label": raw_name}
            )

            source_sha256 = generator._sha256(raw_trace_path)
            repaired_metadata = {
                **raw_metadata,
                "repair_mode": "posthoc",
                "repair_source_system_name": raw_name,
                "repair_source_trace_sha256": source_sha256,
            }
            repaired_trace_metadata = {**repaired_metadata, "provider_calls_added": 0}
            repaired_trace: list[dict[str, Any]] = []
            for index, raw_row in enumerate(raw_trace, start=1):
                task_id = str(raw_row["task_id"])
                repair_applied = index in {1, 2}
                raw_output = raw_row["raw_output"]
                raw_ids = [str(selection["candidate_id"]) for selection in raw_output["selections"]]
                final_ids = (
                    [f"{task_id}_fallback_{rank}" for rank in range(1, 11)]
                    if index == 1
                    else raw_ids
                )
                repaired_trace.append(
                    {
                        "task_id": task_id,
                        "system_name": repaired_name,
                        "metadata": {
                            **repaired_trace_metadata,
                            "repair_applied": repair_applied,
                        },
                        "output": _output_payload(task_id, repaired_name, final_ids),
                        "raw_output": raw_output,
                        "issues": [],
                        "raw_issues": raw_row["raw_issues"],
                        "repaired": repair_applied,
                    }
                )
            repaired_scores = [
                {
                    "task_id": task_id,
                    "system_name": repaired_name,
                    "metadata": repaired_metadata,
                }
                for task_id in task_ids
            ]
            _write_jsonl(run_root / "posthoc_repair.trace.jsonl", repaired_trace)
            _write_jsonl(run_root / "posthoc_scores/card_scores.jsonl", repaired_scores)
            repaired_summary = _metric_summary(
                repaired_name,
                interface,
                condition,
                utility=utility + 0.5,
                repaired=True,
                repaired_rate=2 / 91,
                source_sha256=source_sha256,
            )
            _write_json(run_root / "posthoc_scores/summary.json", repaired_summary)
            comparison_rows.append(
                {**repaired_summary, "system_group": "LLM", "display_label": repaired_name}
            )

            manifest_runs.append(
                {
                    "system_name": interface,
                    "model_config_id": condition,
                    "run_label": raw_name,
                }
            )
            for metric in generator.PAIRED_METRICS:
                all_pair_rows.append(
                    {
                        "comparison": "all_primary_pairs",
                        "metric": metric,
                        "system_a": raw_name,
                        "system_b": repaired_name,
                        "n_cards": 91,
                        "mean_delta": -0.5,
                        "ci_low": -0.75,
                        "ci_high": -0.25,
                    }
                )
            utility += 1.0

    _write_json(
        matrix_root / "manifest.json",
        {
            "systems": list(generator.PRIMARY_LLM_INTERFACES),
            "model_conditions": list(generator.PRIMARY_LLM_CONDITIONS),
            "runs": manifest_runs,
        },
    )
    _write_json(comparison_root / "system_comparison.json", comparison_rows)
    pair_fields = [
        "comparison",
        "metric",
        "system_a",
        "system_b",
        "n_cards",
        "mean_delta",
        "ci_low",
        "ci_high",
    ]
    _write_csv(comparison_root / "paired_bootstrap_deltas.csv", all_pair_rows, pair_fields)

    best_llm = comparison_rows[-1]["system_name"]
    key_rows = [
        {
            "comparison": "best_qsar_minus_best_final_llm",
            "metric": metric,
            "system_a": "qsar_svm",
            "system_b": best_llm,
            "n_cards": 91,
            "mean_delta": 1.25,
            "ci_low": 0.5,
            "ci_high": 2.0,
        }
        for metric in generator.PAIRED_METRICS
    ]
    _write_csv(comparison_root / "paired_bootstrap_key_deltas.csv", key_rows, pair_fields)
    return raw_trace_paths


def test_tracked_manuscript_numbers_are_current_and_byte_stable() -> None:
    generator = _load_generator()

    results_first = generator.render_results(ROOT)
    results_second = generator.render_results(ROOT)
    table_first = generator.render_baseline_rows(ROOT)
    table_second = generator.render_baseline_rows(ROOT)
    attribution_csv_first = generator.render_repair_attribution_csv(ROOT)
    attribution_csv_second = generator.render_repair_attribution_csv(ROOT)
    attribution_tex_first = generator.render_repair_attribution_rows(ROOT)
    attribution_tex_second = generator.render_repair_attribution_rows(ROOT)

    assert results_first == results_second
    assert table_first == table_second
    assert attribution_csv_first == attribution_csv_second
    assert attribution_tex_first == attribution_tex_second
    assert results_first == (ROOT / "paper/manuscript/generated_results.tex").read_text(
        encoding="utf-8"
    )
    assert table_first == (ROOT / "paper/tables/v0.1.0/deterministic_baseline_rows.tex").read_text(
        encoding="utf-8"
    )
    assert attribution_csv_first == (
        ROOT / "paper/manuscript/revision_repair_attribution.csv"
    ).read_text(encoding="utf-8")
    assert attribution_tex_first == (
        ROOT / "paper/tables/v0.1.0/repair_attribution_rows.tex"
    ).read_text(encoding="utf-8")
    assert r"\llmresultsavailabletrue" in results_first
    assert r"Bare LLM + post-hoc repair - OpenAI" in results_first


def test_llm_result_gate_rejects_partial_comparison(tmp_path: Path) -> None:
    generator = _load_generator()
    _write_complete_llm_evidence(tmp_path, generator)
    comparison_path = tmp_path / "release/v0.1.0/experiments/llm/comparison/system_comparison.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    _write_json(comparison_path, comparison[:-1])

    with pytest.raises(ValueError, match="frozen raw-plus-repaired matrix"):
        generator._load_llm_result(tmp_path, expected_cards=91)


def test_llm_result_gate_rejects_mis_scoped_trace(tmp_path: Path) -> None:
    generator = _load_generator()
    trace_paths = _write_complete_llm_evidence(tmp_path, generator)
    trace_path = trace_paths[
        generator._raw_llm_name(
            generator.PRIMARY_LLM_INTERFACES[0], generator.PRIMARY_LLM_CONDITIONS[0]
        )
    ]
    trace = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    trace[-1]["task_id"] = "different_benchmark_task"
    _write_jsonl(trace_path, trace)

    with pytest.raises(ValueError, match="task coverage does not match the frozen cards"):
        generator._load_llm_result(tmp_path, expected_cards=91)


def test_llm_result_gate_accepts_only_complete_frozen_shape(tmp_path: Path) -> None:
    generator = _load_generator()
    _write_minimal_baselines(tmp_path, generator)
    _write_complete_llm_evidence(tmp_path, generator)

    rendered = generator.render_results(tmp_path)

    assert r"\llmresultsavailabletrue" in rendered
    assert r"\llmresultsavailablefalse" not in rendered
    assert r"\newcommand{\BestLLMUtility}{75.500}" in rendered
    assert r"\newcommand{\BestQSARMinusLLMUtility}{1.250}" in rendered
    assert r"\newcommand{\TotalLLMCost}{6.000}" in rendered


def test_repair_attribution_derives_fallback_positions_from_matched_traces(
    tmp_path: Path,
) -> None:
    generator = _load_generator()
    _write_complete_llm_evidence(tmp_path, generator)

    rows, _ = generator._repair_attribution_sources(
        tmp_path,
        expected_cards=91,
        final_slots_per_card=10,
    )

    assert len(rows) == 6
    assert rows[0] == {
        "provider": "OpenAI",
        "interface": "basic",
        "n_cards": 91,
        "cards_repaired": 2,
        "repair_rate": 2 / 91,
        "cards_with_replaced_identity": 1,
        "fallback_supplied_slots": 10,
        "total_final_slots": 910,
        "fallback_slot_rate": 10 / 910,
        "mean_fallback_slots_all_cards": 10 / 91,
        "median_fallback_slots_all_cards": 0,
        "min_fallback_slots_all_cards": 0,
        "max_fallback_slots_all_cards": 10,
        "mean_fallback_slots_repaired_cards": 5,
        "median_fallback_slots_repaired_cards": 5.0,
        "min_fallback_slots_repaired_cards": 0,
        "max_fallback_slots_repaired_cards": 10,
        "repaired_cards_with_zero_fallback_slots": 1,
        "cards_with_all_10_fallback_slots": 1,
    }
    rendered = generator.render_repair_attribution_rows(tmp_path)
    assert "OpenAI, basic & 2/91 (2.20\\%) & 1/91 & 10/910 (1.10\\%)" in rendered
    assert "5.00; 5 (0--10) & 1 & 1" in rendered
    compact = rendered.split(r"\newcommand{\RepairAttributionCompactRows}{%", maxsplit=1)[1]
    assert "OpenAI, basic & 2/91 (2.20\\%) & 1/91 & 10/910 (1.10\\%) & 1" in compact
    assert "5.00; 5 (0--10)" not in compact


def test_repair_attribution_rejects_non_ten_slot_final_action(tmp_path: Path) -> None:
    generator = _load_generator()
    _write_complete_llm_evidence(tmp_path, generator)
    repaired_path = (
        tmp_path
        / "release/v0.1.0/experiments/llm/matrix"
        / generator.PRIMARY_LLM_CONDITIONS[0]
        / generator.PRIMARY_LLM_INTERFACES[0]
        / "posthoc_repair.trace.jsonl"
    )
    rows = [json.loads(line) for line in repaired_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["output"]["selections"] = rows[0]["output"]["selections"][:-1]
    _write_jsonl(repaired_path, rows)

    with pytest.raises(ValueError, match="exactly 10 final selections"):
        generator.render_repair_attribution_csv(tmp_path)


def test_repair_attribution_rejects_unmatched_repaired_task(tmp_path: Path) -> None:
    generator = _load_generator()
    _write_complete_llm_evidence(tmp_path, generator)
    repaired_path = (
        tmp_path
        / "release/v0.1.0/experiments/llm/matrix"
        / generator.PRIMARY_LLM_CONDITIONS[0]
        / generator.PRIMARY_LLM_INTERFACES[0]
        / "posthoc_repair.trace.jsonl"
    )
    rows = [json.loads(line) for line in repaired_path.read_text(encoding="utf-8").splitlines()]
    rows[-1]["task_id"] = "unmatched_task"
    _write_jsonl(repaired_path, rows)

    with pytest.raises(ValueError, match="task coverage does not match"):
        generator.render_repair_attribution_csv(tmp_path)
