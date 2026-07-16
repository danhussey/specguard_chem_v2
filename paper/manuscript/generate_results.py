#!/usr/bin/env python3
"""Generate manuscript numbers from the canonical v0.1.0 result artifacts.

The output deliberately contains no timestamps, absolute paths, or other
machine-local values. Repeated runs over identical release artifacts therefore
produce identical bytes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

BASELINE_ORDER = (
    "oracle_valid_topk",
    "qsar_svm",
    "qsar_rf",
    "qsar_gbt",
    "similarity_to_best_active",
    "random_valid",
    "rules_only",
)

TABLE_LABELS = {
    "oracle_valid_topk": r"Oracle valid top-$k$",
    "qsar_svm": "QSAR linear SVR",
    "qsar_rf": "QSAR random forest",
    "qsar_gbt": "QSAR gradient boosting",
    "similarity_to_best_active": "Similarity to best active",
    "random_valid": "Random valid",
    "rules_only": "Rules/desirability",
}

SUMMARY_FIELDS = (
    "num_cards",
    "feasible_utility",
    "feasible_utility_ci_low",
    "feasible_utility_ci_high",
    "ndcg_at_k",
    "constrained_regret",
    "action_validity",
    "compliance_rate",
    "valid_selected_count",
)

PRIMARY_LLM_INTERFACES = ("bare_llm", "llm_tools")
PRIMARY_LLM_CONDITIONS = (
    "openai_gpt_5_5_2026_04_23_selector",
    "anthropic_opus_4_8_selector",
    "deepseek_v4_pro_2026_07_16_selector",
)
POSTHOC_REPAIR_SUFFIX = "posthoc_repair"
LLM_RESULT_FIELDS = (
    "num_cards",
    "feasible_utility",
    "ndcg_at_k",
    "constrained_regret",
    "action_validity",
    "raw_feasible_utility",
    "raw_ndcg_at_k",
    "raw_action_validity",
)
PAIRED_METRICS = ("feasible_utility", "ndcg_at_k", "action_validity")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"required artifact does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON artifact {path}: {exc}") from exc


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ValueError(f"required artifact does not exist: {path}") from exc

    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL artifact {path}:{line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(row)
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except FileNotFoundError as exc:
        raise ValueError(f"required artifact does not exist: {path}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _as_finite_float(row: dict[str, Any], field: str, *, source: Path) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{source}: missing or non-numeric field {field!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"{source}: non-finite field {field!r}")
    return value


def _load_baselines(repo_root: Path) -> tuple[dict[str, dict[str, Any]], Path]:
    baseline_root = repo_root / "release/v0.1.0/experiments/baselines"
    comparison_path = baseline_root / "comparison/system_comparison.json"
    comparison = _read_json(comparison_path)
    if not isinstance(comparison, list):
        raise ValueError(f"{comparison_path}: expected a JSON array")

    rows: dict[str, dict[str, Any]] = {}
    for raw_row in comparison:
        if not isinstance(raw_row, dict):
            raise ValueError(f"{comparison_path}: every row must be an object")
        name = raw_row.get("system_name")
        if name not in BASELINE_ORDER:
            continue
        if name in rows:
            raise ValueError(f"{comparison_path}: duplicate system row {name!r}")
        rows[name] = raw_row

    missing = [name for name in BASELINE_ORDER if name not in rows]
    if missing:
        raise ValueError(f"{comparison_path}: missing baseline rows: {', '.join(missing)}")

    # Treat per-system summaries as an independent canonical cross-check. The
    # comparison JSON rounds some floats, so equality is numerical rather than
    # byte-for-byte.
    for name in BASELINE_ORDER:
        summary_path = baseline_root / name / "scores/summary.json"
        summary = _read_json(summary_path)
        if not isinstance(summary, dict):
            raise ValueError(f"{summary_path}: expected a JSON object")
        if summary.get("system_name") != name:
            raise ValueError(
                f"{summary_path}: system_name {summary.get('system_name')!r} does not match {name!r}"
            )
        for field in SUMMARY_FIELDS:
            comparison_value = _as_finite_float(rows[name], field, source=comparison_path)
            summary_value = _as_finite_float(summary, field, source=summary_path)
            if not math.isclose(comparison_value, summary_value, rel_tol=0.0, abs_tol=5e-9):
                raise ValueError(
                    f"comparison/summary mismatch for {name}.{field}: "
                    f"{comparison_value} != {summary_value}"
                )

    card_counts = {
        _as_exact_int(
            _as_finite_float(rows[name], "num_cards", source=comparison_path),
            description=f"{comparison_path}: {name}.num_cards",
        )
        for name in BASELINE_ORDER
    }
    if len(card_counts) != 1:
        raise ValueError(f"{comparison_path}: inconsistent baseline card counts: {card_counts}")
    return rows, comparison_path


def _format_number(value: Any) -> str:
    return f"{float(value):.3f}"


def _as_exact_int(value: Any, *, description: str) -> int:
    number = float(value)
    rounded = round(number)
    if not math.isfinite(number) or not math.isclose(number, rounded, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"{description} must be an integer, got {value!r}")
    return int(rounded)


def _tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def _raw_llm_name(interface: str, condition: str) -> str:
    return f"{interface}__{condition}"


def _repaired_llm_name(interface: str, condition: str) -> str:
    return f"{_raw_llm_name(interface, condition)}__{POSTHOC_REPAIR_SUFFIX}"


def _require_exact_task_coverage(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    expected_tasks: set[str],
    expected_system_name: str,
) -> None:
    task_ids: list[str] = []
    for row in rows:
        task_id = row.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(f"{path}: every row must contain a non-empty task_id")
        if row.get("system_name") != expected_system_name:
            raise ValueError(
                f"{path}: expected system_name {expected_system_name!r}, "
                f"got {row.get('system_name')!r} for {task_id}"
            )
        task_ids.append(task_id)

    if len(task_ids) != len(set(task_ids)):
        raise ValueError(f"{path}: duplicate task_id records")
    actual_tasks = set(task_ids)
    if actual_tasks != expected_tasks:
        missing = sorted(expected_tasks - actual_tasks)
        extra = sorted(actual_tasks - expected_tasks)
        raise ValueError(
            f"{path}: task coverage does not match the frozen cards "
            f"(missing={missing[:3]}, extra={extra[:3]})"
        )


def _require_metadata(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    expected: dict[str, Any],
) -> None:
    for row in rows:
        metadata = row.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError(f"{path}: every row must contain metadata")
        for field, value in expected.items():
            if metadata.get(field) != value:
                raise ValueError(
                    f"{path}: metadata.{field} must be {value!r}; "
                    f"got {metadata.get(field)!r} for {row.get('task_id', '<unknown>')}"
                )


def _validate_matrix_manifest(matrix_root: Path) -> None:
    manifest_path = matrix_root / "manifest.json"
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"{manifest_path}: expected a JSON object")
    if manifest.get("task_id") is not None:
        raise ValueError(f"{manifest_path}: task-scoped pilot manifest is not a full matrix")
    manifest_systems = manifest.get("systems")
    if (
        not isinstance(manifest_systems, list)
        or len(manifest_systems) != len(PRIMARY_LLM_INTERFACES)
        or set(manifest_systems) != set(PRIMARY_LLM_INTERFACES)
    ):
        raise ValueError(
            f"{manifest_path}: systems must be exactly {list(PRIMARY_LLM_INTERFACES)!r}"
        )
    manifest_conditions = manifest.get("model_conditions")
    if (
        not isinstance(manifest_conditions, list)
        or len(manifest_conditions) != len(PRIMARY_LLM_CONDITIONS)
        or set(manifest_conditions) != set(PRIMARY_LLM_CONDITIONS)
    ):
        raise ValueError(
            f"{manifest_path}: model_conditions must be exactly {list(PRIMARY_LLM_CONDITIONS)!r}"
        )
    runs = manifest.get("runs")
    if not isinstance(runs, list) or not all(isinstance(row, dict) for row in runs):
        raise ValueError(f"{manifest_path}: runs must be an array of objects")
    actual_runs = [
        (
            str(row.get("system_name")),
            str(row.get("model_config_id")),
            str(row.get("run_label")),
        )
        for row in runs
    ]
    expected_runs = [
        (interface, condition, _raw_llm_name(interface, condition))
        for condition in PRIMARY_LLM_CONDITIONS
        for interface in PRIMARY_LLM_INTERFACES
    ]
    if len(actual_runs) != len(expected_runs) or set(actual_runs) != set(expected_runs):
        raise ValueError(f"{manifest_path}: runs do not match the frozen six-condition matrix")


def _validate_llm_artifacts(
    repo_root: Path,
    *,
    expected_tasks: set[str],
    rows_by_name: dict[str, dict[str, Any]],
    comparison_path: Path,
) -> None:
    matrix_root = repo_root / "release/v0.1.0/experiments/llm/matrix"
    _validate_matrix_manifest(matrix_root)

    for condition in PRIMARY_LLM_CONDITIONS:
        for interface in PRIMARY_LLM_INTERFACES:
            raw_name = _raw_llm_name(interface, condition)
            repaired_name = _repaired_llm_name(interface, condition)
            run_root = matrix_root / condition / interface
            raw_trace_path = run_root / "trace.jsonl"
            raw_scores_path = run_root / "scores/card_scores.jsonl"
            raw_summary_path = run_root / "scores/summary.json"
            repaired_trace_path = run_root / "posthoc_repair.trace.jsonl"
            repaired_scores_path = run_root / "posthoc_scores/card_scores.jsonl"
            repaired_summary_path = run_root / "posthoc_scores/summary.json"

            raw_trace = _read_jsonl(raw_trace_path)
            raw_scores = _read_jsonl(raw_scores_path)
            repaired_trace = _read_jsonl(repaired_trace_path)
            repaired_scores = _read_jsonl(repaired_scores_path)
            for path, artifact_rows, system_name in (
                (raw_trace_path, raw_trace, raw_name),
                (raw_scores_path, raw_scores, raw_name),
                (repaired_trace_path, repaired_trace, repaired_name),
                (repaired_scores_path, repaired_scores, repaired_name),
            ):
                _require_exact_task_coverage(
                    path,
                    artifact_rows,
                    expected_tasks=expected_tasks,
                    expected_system_name=system_name,
                )

            raw_metadata = {
                "base_system_name": interface,
                "llm_model_config_id": condition,
            }
            _require_metadata(raw_trace_path, raw_trace, expected=raw_metadata)
            _require_metadata(raw_scores_path, raw_scores, expected=raw_metadata)

            source_sha256 = _sha256(raw_trace_path)
            repaired_metadata = {
                **raw_metadata,
                "repair_mode": "posthoc",
                "repair_source_system_name": raw_name,
                "repair_source_trace_sha256": source_sha256,
            }
            _require_metadata(repaired_trace_path, repaired_trace, expected=repaired_metadata)
            _require_metadata(repaired_scores_path, repaired_scores, expected=repaired_metadata)
            _require_metadata(
                repaired_trace_path,
                repaired_trace,
                expected={"provider_calls_added": 0},
            )

            for name, summary_path in (
                (raw_name, raw_summary_path),
                (repaired_name, repaired_summary_path),
            ):
                summary = _read_json(summary_path)
                if not isinstance(summary, dict):
                    raise ValueError(f"{summary_path}: expected a JSON object")
                row = rows_by_name[name]
                if summary.get("system_name") != name:
                    raise ValueError(f"{summary_path}: system_name does not match {name!r}")
                for field in LLM_RESULT_FIELDS:
                    comparison_value = _as_finite_float(row, field, source=comparison_path)
                    summary_value = _as_finite_float(summary, field, source=summary_path)
                    if not math.isclose(comparison_value, summary_value, rel_tol=0.0, abs_tol=5e-9):
                        raise ValueError(
                            f"comparison/summary mismatch for {name}.{field}: "
                            f"{comparison_value} != {summary_value}"
                        )
                if summary.get("base_system_name") != interface:
                    raise ValueError(f"{summary_path}: base_system_name must be {interface!r}")
                if summary.get("llm_model_config_id") != condition:
                    raise ValueError(f"{summary_path}: llm_model_config_id must be {condition!r}")
                if name == repaired_name:
                    if summary.get("repair_mode") != "posthoc":
                        raise ValueError(f"{summary_path}: repaired summary lacks posthoc mode")
                    if summary.get("repair_source_system_name") != raw_name:
                        raise ValueError(
                            f"{summary_path}: repair source does not match {raw_name!r}"
                        )
                    if summary.get("repair_source_trace_sha256") != source_sha256:
                        raise ValueError(
                            f"{summary_path}: repair source hash does not match {raw_trace_path}"
                        )


def _validate_paired_outputs(
    comparison_root: Path,
    *,
    expected_cards: int,
    raw_names: set[str],
    repaired_names: set[str],
) -> None:
    all_pairs_path = comparison_root / "paired_bootstrap_deltas.csv"
    all_pairs = _read_csv(all_pairs_path)
    for raw_name in sorted(raw_names):
        repaired_name = f"{raw_name}__{POSTHOC_REPAIR_SUFFIX}"
        for metric in PAIRED_METRICS:
            matches = [
                row
                for row in all_pairs
                if row.get("comparison") == "all_primary_pairs"
                and row.get("metric") == metric
                and {row.get("system_a"), row.get("system_b")} == {raw_name, repaired_name}
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"{all_pairs_path}: expected one paired {metric} row for "
                    f"{raw_name} versus {repaired_name}"
                )
            if (
                _as_exact_int(
                    matches[0].get("n_cards"),
                    description=f"{all_pairs_path}: {raw_name}/{repaired_name}.{metric}.n_cards",
                )
                != expected_cards
            ):
                raise ValueError(
                    f"{all_pairs_path}: incomplete paired coverage for "
                    f"{raw_name} versus {repaired_name}"
                )

    key_pairs_path = comparison_root / "paired_bootstrap_key_deltas.csv"
    key_pairs = _read_csv(key_pairs_path)
    llm_names = raw_names | repaired_names
    for metric in PAIRED_METRICS:
        matches = [
            row
            for row in key_pairs
            if row.get("comparison") == "best_qsar_minus_best_final_llm"
            and row.get("metric") == metric
            and str(row.get("system_a", "")).startswith("qsar_")
            and row.get("system_b") in llm_names
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{key_pairs_path}: expected one 91-card best-QSAR/final-LLM {metric} row"
            )
        if (
            _as_exact_int(
                matches[0].get("n_cards"),
                description=f"{key_pairs_path}: {metric}.n_cards",
            )
            != expected_cards
        ):
            raise ValueError(
                f"{key_pairs_path}: incomplete best-QSAR/final-LLM coverage for {metric}"
            )


def _load_llm_result(repo_root: Path, *, expected_cards: int) -> dict[str, Any] | None:
    llm_root = repo_root / "release/v0.1.0/experiments/llm"
    comparison_root = llm_root / "comparison"
    comparison_path = comparison_root / "system_comparison.json"
    if not comparison_path.exists():
        return None

    comparison = _read_json(comparison_path)
    if not isinstance(comparison, list):
        raise ValueError(f"{comparison_path}: expected a JSON array")
    if not all(isinstance(row, dict) for row in comparison):
        raise ValueError(f"{comparison_path}: every row must be an object")
    llm_rows = [
        row
        for row in comparison
        if (
            row.get("system_group") == "LLM"
            or row.get("base_system_name") in {"bare_llm", "llm_tools"}
            or str(row.get("system_name", "")).split("__", 1)[0] in {"bare_llm", "llm_tools"}
        )
    ]
    if not llm_rows:
        raise ValueError(f"{comparison_path}: canonical comparison contains no LLM rows")

    rows_by_name: dict[str, dict[str, Any]] = {}
    for row in llm_rows:
        name = row.get("system_name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{comparison_path}: every LLM row needs a system_name")
        if name in rows_by_name:
            raise ValueError(f"{comparison_path}: duplicate LLM row {name!r}")
        rows_by_name[name] = row

    raw_names = {
        _raw_llm_name(interface, condition)
        for condition in PRIMARY_LLM_CONDITIONS
        for interface in PRIMARY_LLM_INTERFACES
    }
    repaired_names = {f"{raw_name}__{POSTHOC_REPAIR_SUFFIX}" for raw_name in raw_names}
    expected_names = raw_names | repaired_names
    if set(rows_by_name) != expected_names:
        missing = sorted(expected_names - set(rows_by_name))
        extra = sorted(set(rows_by_name) - expected_names)
        raise ValueError(
            f"{comparison_path}: LLM rows do not match the frozen raw-plus-repaired matrix "
            f"(missing={missing}, extra={extra})"
        )

    incomplete = []
    for name, row in rows_by_name.items():
        if (
            _as_exact_int(
                _as_finite_float(row, "num_cards", source=comparison_path),
                description=f"{comparison_path}: {name}.num_cards",
            )
            != expected_cards
        ):
            incomplete.append(name)
    if incomplete:
        raise ValueError(
            f"{comparison_path}: LLM rows do not cover all {expected_cards} cards: "
            + ", ".join(sorted(incomplete))
        )

    cards_path = repo_root / "data/releases/v0.1.0/system_input_cards.jsonl"
    card_rows = _read_jsonl(cards_path)
    card_task_ids = [row.get("task_id") for row in card_rows]
    if not all(isinstance(task_id, str) and task_id for task_id in card_task_ids):
        raise ValueError(f"{cards_path}: every row must contain a non-empty task_id")
    expected_tasks = set(card_task_ids)
    if len(card_task_ids) != expected_cards or len(expected_tasks) != expected_cards:
        raise ValueError(
            f"{cards_path}: expected {expected_cards} unique frozen task IDs, "
            f"got {len(card_task_ids)} rows and {len(expected_tasks)} unique IDs"
        )

    _validate_llm_artifacts(
        repo_root,
        expected_tasks=expected_tasks,
        rows_by_name=rows_by_name,
        comparison_path=comparison_path,
    )
    _validate_paired_outputs(
        comparison_root,
        expected_cards=expected_cards,
        raw_names=raw_names,
        repaired_names=repaired_names,
    )
    return max(
        rows_by_name.values(),
        key=lambda row: _as_finite_float(row, "feasible_utility", source=comparison_path),
    )


def render_results(repo_root: Path) -> str:
    rows, comparison_path = _load_baselines(repo_root)
    num_cards = _as_exact_int(
        rows[BASELINE_ORDER[0]]["num_cards"], description="baseline num_cards"
    )
    selection_counts = {
        _as_exact_int(
            rows[name]["valid_selected_count"],
            description=f"{name}.valid_selected_count",
        )
        for name in BASELINE_ORDER
    }
    if len(selection_counts) != 1:
        raise ValueError(f"baseline summaries disagree on selected batch size: {selection_counts}")
    budget_k = selection_counts.pop()

    qsar_rows = [rows[name] for name in ("qsar_svm", "qsar_rf", "qsar_gbt")]
    best_qsar = max(qsar_rows, key=lambda row: float(row["feasible_utility"]))
    llm_result = _load_llm_result(repo_root, expected_cards=num_cards)

    output = [
        "% Generated by paper/manuscript/generate_results.py; do not edit by hand.",
        "% Canonical baseline source: release/v0.1.0/experiments/baselines/comparison/system_comparison.json",
        f"% Canonical baseline source SHA256: {_sha256(comparison_path)}",
        "% Values were cross-checked against every per-system scores/summary.json artifact.",
        r"\newif\ifllmresultsavailable",
        r"\llmresultsavailabletrue" if llm_result is not None else r"\llmresultsavailablefalse",
        "",
        rf"\newcommand{{\NumCards}}{{{num_cards}}}",
        rf"\newcommand{{\BudgetK}}{{{budget_k}}}",
        rf"\newcommand{{\BestQSARUtility}}{{{_format_number(best_qsar['feasible_utility'])}}}",
        rf"\newcommand{{\BestQSARNDCG}}{{{_format_number(best_qsar['ndcg_at_k'])}}}",
        rf"\newcommand{{\BestQSARRegret}}{{{_format_number(best_qsar['constrained_regret'])}}}",
        rf"\newcommand{{\SimilarityUtility}}{{{_format_number(rows['similarity_to_best_active']['feasible_utility'])}}}",
        rf"\newcommand{{\RandomUtility}}{{{_format_number(rows['random_valid']['feasible_utility'])}}}",
        rf"\newcommand{{\RulesUtility}}{{{_format_number(rows['rules_only']['feasible_utility'])}}}",
        rf"\newcommand{{\OracleUtility}}{{{_format_number(rows['oracle_valid_topk']['feasible_utility'])}}}",
        "",
    ]

    if llm_result is None:
        output.extend(
            [
                "% No canonical corrected LLM comparison artifact exists; keep the paper in pre-run mode.",
                r"\newcommand{\BestLLMLabel}{PENDING}",
                r"\newcommand{\BestLLMUtility}{PENDING}",
                r"\newcommand{\BestLLMNDCG}{PENDING}",
                r"\newcommand{\BestLLMActionValidity}{PENDING}",
                r"\newcommand{\BestLLMCost}{PENDING}",
            ]
        )
    else:
        label = str(llm_result.get("display_label") or llm_result.get("system_name"))
        cost = next(
            (
                llm_result[field]
                for field in ("actual_cost_usd", "total_cost_usd", "estimated_cost_usd")
                if field in llm_result and llm_result[field] is not None
            ),
            "NOT REPORTED",
        )
        cost_text = _format_number(cost) if isinstance(cost, (int, float)) else str(cost)
        output.extend(
            [
                "% Populated from the canonical corrected LLM comparison artifact.",
                rf"\newcommand{{\BestLLMLabel}}{{{_tex_escape(label)}}}",
                rf"\newcommand{{\BestLLMUtility}}{{{_format_number(llm_result['feasible_utility'])}}}",
                rf"\newcommand{{\BestLLMNDCG}}{{{_format_number(llm_result['ndcg_at_k'])}}}",
                rf"\newcommand{{\BestLLMActionValidity}}{{{_format_number(llm_result['raw_action_validity'])}}}",
                rf"\newcommand{{\BestLLMCost}}{{{_tex_escape(cost_text)}}}",
            ]
        )
    return "\n".join(output) + "\n"


def render_baseline_rows(repo_root: Path) -> str:
    rows, comparison_path = _load_baselines(repo_root)
    output = [
        "% Generated by paper/manuscript/generate_results.py; do not edit by hand.",
        "% Canonical source: release/v0.1.0/experiments/baselines/comparison/system_comparison.json",
        f"% Canonical source SHA256: {_sha256(comparison_path)}",
        r"\newcommand{\DeterministicBaselineRows}{%",
    ]
    for name in BASELINE_ORDER:
        row = rows[name]
        utility = _format_number(row["feasible_utility"])
        utility_low = _format_number(row["feasible_utility_ci_low"])
        utility_high = _format_number(row["feasible_utility_ci_high"])
        output.append(
            f"{TABLE_LABELS[name]} & {utility} ({utility_low}--{utility_high}) & "
            f"{_format_number(row['ndcg_at_k'])} & "
            f"{_format_number(row['constrained_regret'])} & "
            f"{_format_number(row['action_validity'])} \\\\%"
        )
    output.append("}")
    return "\n".join(output) + "\n"


def _write_or_check(path: Path, content: str, *, check: bool) -> bool:
    if check:
        return path.exists() and path.read_text(encoding="utf-8") == content
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify tracked outputs match the canonical artifacts without writing",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    outputs = {
        repo_root / "paper/manuscript/generated_results.tex": render_results(repo_root),
        repo_root / "paper/tables/v0.1.0/deterministic_baseline_rows.tex": render_baseline_rows(
            repo_root
        ),
    }
    mismatches = [
        path.relative_to(repo_root).as_posix()
        for path, content in outputs.items()
        if not _write_or_check(path, content, check=args.check)
    ]
    if mismatches:
        print("generated manuscript artifacts are stale:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  {mismatch}", file=sys.stderr)
        return 1

    verb = "verified" if args.check else "generated"
    for path in outputs:
        print(f"{verb} {path.relative_to(repo_root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
