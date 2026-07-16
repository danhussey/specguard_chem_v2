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
        for interface in generator.PRIMARY_LLM_INTERFACES:
            raw_name = generator._raw_llm_name(interface, condition)
            repaired_name = generator._repaired_llm_name(interface, condition)
            run_root = matrix_root / condition / interface
            raw_trace_path = run_root / "trace.jsonl"
            raw_trace_paths[raw_name] = raw_trace_path
            raw_metadata = {
                "base_system_name": interface,
                "llm_model_config_id": condition,
            }
            raw_trace = [
                {"task_id": task_id, "system_name": raw_name, "metadata": raw_metadata}
                for task_id in task_ids
            ]
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
            repaired_trace = [
                {
                    "task_id": task_id,
                    "system_name": repaired_name,
                    "metadata": repaired_trace_metadata,
                }
                for task_id in task_ids
            ]
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
    pair_fields = ["comparison", "metric", "system_a", "system_b", "n_cards"]
    _write_csv(comparison_root / "paired_bootstrap_deltas.csv", all_pair_rows, pair_fields)

    best_llm = comparison_rows[-1]["system_name"]
    key_rows = [
        {
            "comparison": "best_qsar_minus_best_final_llm",
            "metric": metric,
            "system_a": "qsar_svm",
            "system_b": best_llm,
            "n_cards": 91,
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

    assert results_first == results_second
    assert table_first == table_second
    assert results_first == (ROOT / "paper/manuscript/generated_results.tex").read_text(
        encoding="utf-8"
    )
    assert table_first == (ROOT / "paper/tables/v0.1.0/deterministic_baseline_rows.tex").read_text(
        encoding="utf-8"
    )
    assert r"\llmresultsavailablefalse" in results_first


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
