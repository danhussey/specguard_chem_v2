from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .chem.constraints import evaluate_candidate, is_candidate_feasible
from .io import load_models, write_jsonl
from .schemas import DecisionCard, RunRecord, SelectionItem, SystemOutput, ValidationIssue
from .systems.baselines import DETERMINISTIC_SYSTEMS, fallback_ranking, run_baseline_system
from .systems.llm import LLM_SYSTEMS, run_llm_system
from .systems.providers import LLMModelConfig


def validate_output(card: DecisionCard, output: SystemOutput) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if output.task_id != card.task_id:
        issues.append(
            ValidationIssue(
                code="task_id_mismatch",
                message=f"Output task_id {output.task_id} does not match {card.task_id}",
            )
        )
    if len(output.selections) != card.budget_k:
        issues.append(
            ValidationIssue(
                code="wrong_k",
                message=f"Expected exactly {card.budget_k} selections, got {len(output.selections)}",
            )
        )

    candidate_by_id = card.candidate_by_id
    seen: set[str] = set()
    for item in output.selections:
        if item.candidate_id in seen:
            issues.append(
                ValidationIssue(
                    code="duplicate",
                    message="Candidate selected more than once",
                    candidate_id=item.candidate_id,
                    rank=item.rank,
                )
            )
            continue
        seen.add(item.candidate_id)
        if item.candidate_id in card.support_ids:
            issues.append(
                ValidationIssue(
                    code="support_selected",
                    message="Selected a support compound",
                    candidate_id=item.candidate_id,
                    rank=item.rank,
                )
            )
            continue
        candidate = candidate_by_id.get(item.candidate_id)
        if candidate is None:
            issues.append(
                ValidationIssue(
                    code="out_of_pool",
                    message="Selected ID is not in the candidate pool",
                    candidate_id=item.candidate_id,
                    rank=item.rank,
                )
            )
            continue
        for candidate_issue in evaluate_candidate(card, candidate):
            issues.append(candidate_issue.model_copy(update={"rank": item.rank}))
    return issues


def repair_output(card: DecisionCard, output: SystemOutput) -> SystemOutput:
    kept: list[str] = []
    seen: set[str] = set()
    for item in output.selections:
        candidate = card.candidate_by_id.get(item.candidate_id)
        if candidate is None:
            continue
        if item.candidate_id in seen:
            continue
        if item.candidate_id in card.support_ids:
            continue
        if not is_candidate_feasible(card, candidate):
            continue
        seen.add(item.candidate_id)
        kept.append(item.candidate_id)

    for candidate in fallback_ranking(card):
        if len(kept) >= card.budget_k:
            break
        if candidate.id not in seen:
            kept.append(candidate.id)
            seen.add(candidate.id)

    selections = [
        SelectionItem(rank=rank, candidate_id=candidate_id)
        for rank, candidate_id in enumerate(kept[: card.budget_k], start=1)
    ]
    metadata = dict(output.metadata)
    metadata["validator_repaired"] = True
    metadata["original_selection_count"] = len(output.selections)
    return SystemOutput(
        task_id=card.task_id,
        system_name=output.system_name,
        selections=selections,
        metadata=metadata,
    )


def run_system_on_card(
    card: DecisionCard,
    system_name: str,
    *,
    seed: int = 7,
    cache_dir: Path | None = None,
    allow_external: bool = False,
    model: str = "gpt-4.1-mini",
    model_config: LLMModelConfig | None = None,
    run_label: str | None = None,
) -> RunRecord:
    if system_name in DETERMINISTIC_SYSTEMS:
        output = run_baseline_system(card, system_name, seed=seed)
    elif system_name in LLM_SYSTEMS:
        output = run_llm_system(
            card,
            system_name,
            cache_dir=cache_dir,
            allow_external=allow_external,
            model=model,
            model_config=model_config,
            run_label=run_label,
        )
    else:
        raise ValueError(f"Unknown system: {system_name}")

    initial_issues = validate_output(card, output)
    repaired = False
    if system_name.endswith("_validator") and initial_issues:
        output = repair_output(card, output)
        repaired = True
    final_issues = validate_output(card, output)
    return RunRecord(
        task_id=card.task_id,
        system_name=output.system_name,
        output=output,
        issues=final_issues,
        repaired=repaired,
        metadata={
            "initial_issue_count": len(initial_issues),
            "base_system_name": system_name,
            "run_label": run_label,
            "llm_provider": output.metadata.get("llm_provider"),
            "llm_model": output.metadata.get("llm_model"),
            "llm_model_config_id": output.metadata.get("llm_model_config_id"),
            "request_sha256": output.metadata.get("request_sha256"),
            "max_tokens": output.metadata.get("max_tokens"),
            "temperature": output.metadata.get("temperature"),
            "reasoning_effort": output.metadata.get("reasoning_effort"),
            "thinking": output.metadata.get("thinking"),
        },
    )


def run_system_on_cards(
    cards: list[DecisionCard],
    system_name: str,
    *,
    seed: int = 7,
    cache_dir: Path | None = None,
    allow_external: bool = False,
    model: str = "gpt-4.1-mini",
    model_config: LLMModelConfig | None = None,
    run_label: str | None = None,
    workers: int = 1,
) -> list[RunRecord]:
    def run_card(card: DecisionCard) -> RunRecord:
        return run_system_on_card(
            card,
            system_name,
            seed=seed,
            cache_dir=cache_dir,
            allow_external=allow_external,
            model=model,
            model_config=model_config,
            run_label=run_label,
        )

    if workers <= 1:
        return [run_card(card) for card in cards]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(run_card, cards))


def run_system_file(
    cards_path: Path,
    system_name: str,
    out: Path,
    *,
    seed: int = 7,
    cache_dir: Path | None = None,
    allow_external: bool = False,
    model: str = "gpt-4.1-mini",
    model_config: LLMModelConfig | None = None,
    run_label: str | None = None,
    workers: int = 1,
) -> list[RunRecord]:
    cards = load_models(cards_path, DecisionCard)
    records = run_system_on_cards(
        cards,
        system_name,
        seed=seed,
        cache_dir=cache_dir,
        allow_external=allow_external,
        model=model,
        model_config=model_config,
        run_label=run_label,
        workers=workers,
    )
    write_jsonl(out, records)
    return records
