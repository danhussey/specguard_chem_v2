from __future__ import annotations

import math
from pathlib import Path
from statistics import mean
from typing import TYPE_CHECKING, Iterable

import numpy as np
import pandas as pd

from .artifacts import load_evaluation_cards
from .chem.constraints import is_candidate_feasible
from .io import load_models, write_json, write_jsonl
from .operational import write_operational_artifacts
from .schemas import CardScore, DecisionCard, RunRecord, SystemOutput, ValidationIssue

if TYPE_CHECKING:
    from .costing import PricingConfig


def _activity_values(card: DecisionCard) -> dict[str, float]:
    return {
        candidate.id: float(candidate.activity_value)
        for candidate in card.candidate_pool
        if candidate.activity_value is not None
    }


def _default_hit_threshold(values: Iterable[float]) -> float | None:
    values_list = list(values)
    if not values_list:
        return None
    return float(np.quantile(values_list, 0.75))


def _dcg(relevances: list[float]) -> float:
    total = 0.0
    for index, relevance in enumerate(relevances, start=1):
        total += max(relevance, 0.0) / math.log2(index + 1)
    return total


def ndcg_at_k(selected_relevances: list[float], ideal_relevances: list[float], k: int) -> float:
    dcg = _dcg(selected_relevances[:k])
    idcg = _dcg(sorted(ideal_relevances, reverse=True)[:k])
    if idcg == 0:
        return 0.0
    return dcg / idcg


def _issue_count(record: RunRecord, code: str) -> int:
    return sum(1 for issue in record.issues if issue.code == code)


def _issue_code_count(issues: list[ValidationIssue], code: str) -> int:
    return sum(1 for issue in issues if issue.code == code)


def _schema_error_count(issues: list[ValidationIssue]) -> int:
    return sum(
        1
        for issue in issues
        if issue.code in {"task_id_mismatch", "wrong_k"} or issue.code.startswith("schema")
    )


def _constraint_violation_count(issues: list[ValidationIssue]) -> int:
    return sum(
        1
        for issue in issues
        if issue.code
        in {
            "descriptor_max",
            "descriptor_min",
            "descriptor_range",
            "forbidden_smarts",
            "invalid_smiles",
        }
    )


def _score_output_metrics(
    card: DecisionCard,
    output: SystemOutput,
    issues: list[ValidationIssue],
    *,
    activity_by_id: dict[str, float],
    feasible_ids: set[str],
    feasible_activities: list[float],
    oracle_utility: float,
    hit_threshold: float | None,
) -> dict[str, object]:
    seen: set[str] = set()
    valid_selected_ids: list[str] = []
    selected_relevances: list[float] = []
    for item in output.selections[: card.budget_k]:
        candidate_id = item.candidate_id
        valid = (
            candidate_id not in seen
            and candidate_id in feasible_ids
            and candidate_id in activity_by_id
        )
        seen.add(candidate_id)
        if valid:
            valid_selected_ids.append(candidate_id)
            selected_relevances.append(activity_by_id[candidate_id])
        else:
            selected_relevances.append(0.0)

    valid_activities = [activity_by_id[candidate_id] for candidate_id in valid_selected_ids]
    feasible_utility = float(sum(valid_activities))
    constrained_regret = max(0.0, oracle_utility - feasible_utility)

    hit_recovery = None
    enrichment = None
    if hit_threshold is not None and feasible_activities:
        pool_hits = [value for value in feasible_activities if value >= hit_threshold]
        selected_hits = [value for value in valid_activities if value >= hit_threshold]
        hit_recovery = (len(selected_hits) / len(pool_hits)) if pool_hits else 0.0
        selected_rate = len(selected_hits) / card.budget_k
        pool_rate = len(pool_hits) / len(feasible_activities)
        enrichment = (selected_rate / pool_rate) if pool_rate else 0.0

    schema_error_count = _schema_error_count(issues)
    return {
        "ndcg_at_k": ndcg_at_k(selected_relevances, feasible_activities, card.budget_k),
        "mean_selected_activity": mean(valid_activities) if valid_activities else None,
        "hit_recovery_at_k": hit_recovery,
        "enrichment_at_k": enrichment,
        "feasible_utility": feasible_utility,
        "constrained_regret": constrained_regret,
        "action_validity": 1.0 if not issues else 0.0,
        "compliance_rate": min(1.0, len(valid_selected_ids) / card.budget_k),
        "schema_error_rate": 1.0 if schema_error_count else 0.0,
        "wrong_k": bool(_issue_code_count(issues, "wrong_k")),
        "pool_violation_count": _issue_code_count(issues, "out_of_pool"),
        "duplicate_count": _issue_code_count(issues, "duplicate"),
        "support_violation_count": _issue_code_count(issues, "support_selected"),
        "constraint_violation_count": _constraint_violation_count(issues),
        "valid_selected_count": len(valid_selected_ids),
        "selection_count": len(output.selections),
    }


def score_record(
    card: DecisionCard, record: RunRecord, *, hit_threshold: float | None = None
) -> CardScore:
    activity_by_id = _activity_values(card)
    feasible_ids = {
        candidate.id for candidate in card.candidate_pool if is_candidate_feasible(card, candidate)
    }
    feasible_activities = [
        activity_by_id[candidate_id]
        for candidate_id in feasible_ids
        if candidate_id in activity_by_id
    ]
    if hit_threshold is None:
        hit_threshold = _default_hit_threshold(feasible_activities)

    ideal_activities = sorted(feasible_activities, reverse=True)[: card.budget_k]
    oracle_utility = float(sum(ideal_activities))
    final_metrics = _score_output_metrics(
        card,
        record.output,
        record.issues,
        activity_by_id=activity_by_id,
        feasible_ids=feasible_ids,
        feasible_activities=feasible_activities,
        oracle_utility=oracle_utility,
        hit_threshold=hit_threshold,
    )
    raw_metrics = None
    if record.raw_output is not None:
        raw_metrics = _score_output_metrics(
            card,
            record.raw_output,
            record.raw_issues,
            activity_by_id=activity_by_id,
            feasible_ids=feasible_ids,
            feasible_activities=feasible_activities,
            oracle_utility=oracle_utility,
            hit_threshold=hit_threshold,
        )
    repair_delta = None
    if raw_metrics is not None:
        repair_delta = float(final_metrics["feasible_utility"]) - float(
            raw_metrics["feasible_utility"]
        )

    return CardScore(
        task_id=card.task_id,
        system_name=record.system_name,
        ndcg_at_k=float(final_metrics["ndcg_at_k"]),
        mean_selected_activity=final_metrics["mean_selected_activity"],
        hit_recovery_at_k=final_metrics["hit_recovery_at_k"],
        enrichment_at_k=final_metrics["enrichment_at_k"],
        feasible_utility=float(final_metrics["feasible_utility"]),
        oracle_utility=oracle_utility,
        constrained_regret=float(final_metrics["constrained_regret"]),
        action_validity=float(final_metrics["action_validity"]),
        compliance_rate=float(final_metrics["compliance_rate"]),
        schema_error_rate=float(final_metrics["schema_error_rate"]),
        wrong_k=bool(final_metrics["wrong_k"]),
        pool_violation_count=int(final_metrics["pool_violation_count"]),
        duplicate_count=int(final_metrics["duplicate_count"]),
        support_violation_count=int(final_metrics["support_violation_count"]),
        constraint_violation_count=int(final_metrics["constraint_violation_count"]),
        valid_selected_count=int(final_metrics["valid_selected_count"]),
        raw_ndcg_at_k=(float(raw_metrics["ndcg_at_k"]) if raw_metrics is not None else None),
        raw_feasible_utility=(
            float(raw_metrics["feasible_utility"]) if raw_metrics is not None else None
        ),
        raw_action_validity=(
            float(raw_metrics["action_validity"]) if raw_metrics is not None else None
        ),
        raw_compliance_rate=(
            float(raw_metrics["compliance_rate"]) if raw_metrics is not None else None
        ),
        raw_schema_error_rate=(
            float(raw_metrics["schema_error_rate"]) if raw_metrics is not None else None
        ),
        raw_valid_selected_count=(
            int(raw_metrics["valid_selected_count"]) if raw_metrics is not None else None
        ),
        raw_selection_count=(
            int(raw_metrics["selection_count"]) if raw_metrics is not None else None
        ),
        repaired_rate=1.0 if record.repaired else 0.0,
        repaired_from_empty_rate=(
            1.0 if record.metadata.get("repaired_from_empty") is True else 0.0
        ),
        repair_delta_feasible_utility=repair_delta,
        hit_threshold=hit_threshold,
        metadata={
            key: value
            for key, value in record.metadata.items()
            if key
            in {
                "base_system_name",
                "run_label",
                "llm_provider",
                "llm_model",
                "llm_model_config_id",
                "request_sha256",
                "prompt_profile",
                "repair_mode",
                "repair_policy",
                "repair_source_trace_sha256",
                "repair_source_system_name",
            }
            and value is not None
        },
    )


def _bootstrap_ci(
    values: list[float],
    *,
    samples: int = 1000,
    seed: int = 7,
) -> dict[str, float] | None:
    if not values:
        return None
    if len(values) == 1 or samples <= 0:
        value = float(values[0])
        return {"mean": value, "ci_low": value, "ci_high": value}
    rng = np.random.default_rng(seed)
    arr = np.array(values, dtype=float)
    means = []
    for _ in range(samples):
        means.append(float(np.mean(rng.choice(arr, size=len(arr), replace=True))))
    return {
        "mean": float(np.mean(arr)),
        "ci_low": float(np.quantile(means, 0.025)),
        "ci_high": float(np.quantile(means, 0.975)),
    }


def summarize_scores(
    scores: list[CardScore],
    *,
    bootstrap_samples: int = 1000,
    seed: int = 7,
) -> dict[str, object]:
    if not scores:
        return {"num_cards": 0}
    numeric_fields = [
        "ndcg_at_k",
        "mean_selected_activity",
        "hit_recovery_at_k",
        "enrichment_at_k",
        "feasible_utility",
        "oracle_utility",
        "constrained_regret",
        "action_validity",
        "compliance_rate",
        "schema_error_rate",
        "pool_violation_count",
        "duplicate_count",
        "support_violation_count",
        "constraint_violation_count",
        "valid_selected_count",
        "raw_ndcg_at_k",
        "raw_feasible_utility",
        "raw_action_validity",
        "raw_compliance_rate",
        "raw_schema_error_rate",
        "raw_valid_selected_count",
        "raw_selection_count",
        "repaired_rate",
        "repaired_from_empty_rate",
        "repair_delta_feasible_utility",
    ]
    summary: dict[str, object] = {
        "system_name": scores[0].system_name,
        "num_cards": len(scores),
    }
    for metadata_key in [
        "base_system_name",
        "llm_provider",
        "llm_model",
        "llm_model_config_id",
        "repair_mode",
        "repair_policy",
        "repair_source_trace_sha256",
        "repair_source_system_name",
    ]:
        values = {
            str(score.metadata[metadata_key])
            for score in scores
            if score.metadata.get(metadata_key) is not None
        }
        if len(values) == 1:
            summary[metadata_key] = values.pop()
    for field in numeric_fields:
        values = [getattr(score, field) for score in scores]
        filtered = [float(value) for value in values if value is not None]
        summary[field] = float(mean(filtered)) if filtered else None
        if field in {
            "ndcg_at_k",
            "feasible_utility",
            "constrained_regret",
            "action_validity",
            "compliance_rate",
            "raw_ndcg_at_k",
            "raw_feasible_utility",
            "raw_action_validity",
            "raw_compliance_rate",
        }:
            ci = _bootstrap_ci(filtered, samples=bootstrap_samples, seed=seed)
            if ci is not None:
                summary[f"{field}_ci_low"] = ci["ci_low"]
                summary[f"{field}_ci_high"] = ci["ci_high"]
    summary["wrong_k_rate"] = float(mean([1.0 if score.wrong_k else 0.0 for score in scores]))
    summary["regret_fraction"] = (
        float(summary["constrained_regret"]) / float(summary["oracle_utility"])
        if summary.get("oracle_utility")
        else None
    )
    return summary


def failure_taxonomy(records: list[RunRecord]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in records:
        if not record.issues:
            rows.append(
                {
                    "task_id": record.task_id,
                    "system_name": record.system_name,
                    "failure_type": "none",
                    "count": 0,
                }
            )
            continue
        counts: dict[str, int] = {}
        for issue in record.issues:
            if issue.code in {"wrong_k", "task_id_mismatch"} or issue.code.startswith("schema"):
                failure_type = "schema_failure"
            elif issue.code in {"out_of_pool", "duplicate", "support_selected"}:
                failure_type = "selection_contract_failure"
            elif issue.code in {
                "descriptor_max",
                "descriptor_min",
                "descriptor_range",
                "forbidden_smarts",
                "invalid_smiles",
            }:
                failure_type = "constraint_failure"
            else:
                failure_type = "other_failure"
            counts[failure_type] = counts.get(failure_type, 0) + 1
        for failure_type, count in sorted(counts.items()):
            rows.append(
                {
                    "task_id": record.task_id,
                    "system_name": record.system_name,
                    "failure_type": failure_type,
                    "count": count,
                }
            )
    return pd.DataFrame(rows)


def metric_denominators(scores: list[CardScore]) -> dict[str, object]:
    return {
        "num_cards": len(scores),
        "cards_with_mean_activity": sum(
            score.mean_selected_activity is not None for score in scores
        ),
        "cards_with_hit_recovery": sum(score.hit_recovery_at_k is not None for score in scores),
        "cards_with_enrichment": sum(score.enrichment_at_k is not None for score in scores),
        "cards_with_raw_metrics": sum(score.raw_feasible_utility is not None for score in scores),
        "cards_with_nonzero_oracle_utility": sum(score.oracle_utility > 0 for score in scores),
    }


def score_run(
    cards_path: Path,
    run_path: Path,
    out_dir: Path,
    *,
    hit_threshold: float | None = None,
    bootstrap_samples: int = 1000,
    seed: int = 7,
    scorer_outcomes_path: Path | None = None,
    pricing: PricingConfig | None = None,
) -> list[CardScore]:
    loaded_cards = load_evaluation_cards(cards_path, scorer_outcomes_path)
    missing_outcomes = [
        (card.task_id, candidate.id)
        for card in loaded_cards
        for candidate in card.candidate_pool
        if candidate.activity_value is None
    ]
    if missing_outcomes:
        task_id, candidate_id = missing_outcomes[0]
        raise ValueError(
            f"scoring requires candidate outcomes; missing outcome for {task_id}/{candidate_id}"
        )
    cards: dict[str, DecisionCard] = {}
    for card in loaded_cards:
        if card.task_id in cards:
            raise ValueError(f"duplicate decision-card task_id: {card.task_id}")
        cards[card.task_id] = card
    records = load_models(run_path, RunRecord)
    seen_record_tasks: set[str] = set()
    scores: list[CardScore] = []
    for record in records:
        if record.task_id in seen_record_tasks:
            raise ValueError(f"duplicate run task_id: {record.task_id}")
        seen_record_tasks.add(record.task_id)
        if record.task_id not in cards:
            raise ValueError(f"run task_id is not present in decision cards: {record.task_id}")
        scores.append(score_record(cards[record.task_id], record, hit_threshold=hit_threshold))
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "card_scores.jsonl", scores)
    summary = summarize_scores(scores, bootstrap_samples=bootstrap_samples, seed=seed)
    summary.update(write_operational_artifacts(records, out_dir, pricing=pricing))
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "metric_denominators.json", metric_denominators(scores))
    failure_taxonomy(records).to_csv(out_dir / "failure_taxonomy.csv", index=False)
    return scores
