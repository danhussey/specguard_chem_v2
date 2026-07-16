from __future__ import annotations

from pathlib import Path

from .artifacts import (
    load_evaluation_cards,
    sha256_file,
    system_input_payload,
)
from .io import load_models, write_jsonl
from .runner import repair_output, validate_output
from .schemas import DecisionCard, RunRecord, SystemOutput, ValidationIssue

POSTHOC_REPAIR_POLICY = "specguard.deterministic-harness-repair.v1"
POSTHOC_REPAIR_SUFFIX = "posthoc_repair"
POSTHOC_REPAIR_SOURCE_SYSTEMS = frozenset({"bare_llm", "llm_tools"})


def _issue_payloads(issues: list[ValidationIssue]) -> list[dict[str, object]]:
    return [issue.model_dump(mode="json") for issue in issues]


def _source_base_system_name(record: RunRecord, raw_output: SystemOutput) -> str:
    for metadata in (record.metadata, raw_output.metadata):
        value = metadata.get("base_system_name")
        if value:
            return str(value)
    return record.system_name.split("__", 1)[0]


def apply_posthoc_repair(
    card: DecisionCard,
    record: RunRecord,
    *,
    source_trace_sha256: str,
) -> RunRecord:
    """Apply the harness repair to one already-recorded raw LLM response.

    The function never invokes a model provider. It keeps the source raw output
    and issues as the transformed record's ``raw_*`` fields, while placing the
    independently attributable repaired view in ``output`` and ``issues``.
    """

    if not source_trace_sha256:
        raise ValueError("source_trace_sha256 is required for post-hoc repair attribution")
    if record.repaired or record.metadata.get("repair_mode") == "posthoc":
        raise ValueError(f"run record {record.task_id} has already been repaired")

    if record.raw_output is None:
        raw_output = record.output.model_copy(deep=True)
        raw_issues = [issue.model_copy(deep=True) for issue in record.issues]
        raw_source_field = "output"
    else:
        raw_output = record.raw_output.model_copy(deep=True)
        raw_issues = [issue.model_copy(deep=True) for issue in record.raw_issues]
        raw_source_field = "raw_output"

    source_base_system = _source_base_system_name(record, raw_output)
    if source_base_system not in POSTHOC_REPAIR_SOURCE_SYSTEMS:
        allowed = ", ".join(sorted(POSTHOC_REPAIR_SOURCE_SYSTEMS))
        raise ValueError(
            f"post-hoc repair only accepts raw {allowed} traces; "
            f"got {source_base_system!r} for {record.task_id}"
        )

    current_raw_issues = validate_output(card, raw_output)
    if _issue_payloads(raw_issues) != _issue_payloads(current_raw_issues):
        raise ValueError(
            f"preserved raw issues do not match current validation for {record.task_id}; "
            "refusing to rewrite source evidence"
        )

    repaired = bool(raw_issues)
    if repaired:
        final_output = repair_output(card, raw_output)
    else:
        final_output = raw_output.model_copy(deep=True)

    repaired_system_name = f"{record.system_name}__{POSTHOC_REPAIR_SUFFIX}"
    repaired_from_empty = repaired and not raw_output.selections
    attribution: dict[str, object] = {
        "repair_mode": "posthoc",
        "repair_policy": POSTHOC_REPAIR_POLICY,
        "repair_source_trace_sha256": source_trace_sha256,
        "repair_source_system_name": record.system_name,
        "repair_source_base_system_name": source_base_system,
        "repair_raw_source_field": raw_source_field,
        "repair_evaluated": True,
        "repair_applied": repaired,
        "provider_calls_added": 0,
    }
    final_output = final_output.model_copy(
        update={
            "system_name": repaired_system_name,
            "metadata": {**final_output.metadata, **attribution},
        },
        deep=True,
    )
    final_issues = validate_output(card, final_output)
    metadata = {
        **record.metadata,
        **attribution,
        "base_system_name": source_base_system,
        "run_label": repaired_system_name,
        "initial_issue_count": len(raw_issues),
        "raw_issue_count": len(raw_issues),
        "final_issue_count": len(final_issues),
        "validator_repaired": repaired,
        "original_selection_count": len(raw_output.selections) if repaired else None,
        "repaired_from_empty": repaired_from_empty,
    }
    return RunRecord(
        task_id=record.task_id,
        system_name=repaired_system_name,
        output=final_output,
        issues=final_issues,
        raw_output=raw_output,
        raw_issues=raw_issues,
        repaired=repaired,
        metadata=metadata,
    )


def repair_llm_trace_file(cards_path: Path, run_path: Path, out: Path) -> list[RunRecord]:
    """Create a deterministic repaired view of a raw LLM trace.

    Candidate outcomes are projected away before repair. The source trace is
    hash-bound into every output record and cannot be overwritten in place.
    """

    if run_path.resolve() == out.resolve():
        raise ValueError("post-hoc repair output must not overwrite the source trace")

    cards: dict[str, DecisionCard] = {}
    for loaded_card in load_evaluation_cards(cards_path):
        card = DecisionCard.model_validate(system_input_payload(loaded_card))
        if card.task_id in cards:
            raise ValueError(f"duplicate decision-card task_id: {card.task_id}")
        cards[card.task_id] = card

    records = load_models(run_path, RunRecord)
    source_trace_sha256 = sha256_file(run_path)
    transformed: list[RunRecord] = []
    seen_tasks: set[str] = set()
    for record in records:
        if record.task_id in seen_tasks:
            raise ValueError(f"duplicate run task_id: {record.task_id}")
        seen_tasks.add(record.task_id)
        card = cards.get(record.task_id)
        if card is None:
            raise ValueError(f"run task_id is not present in decision cards: {record.task_id}")
        transformed.append(
            apply_posthoc_repair(
                card,
                record,
                source_trace_sha256=source_trace_sha256,
            )
        )

    write_jsonl(out, transformed)
    return transformed
