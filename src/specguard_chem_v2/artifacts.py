from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .io import read_jsonl, write_jsonl
from .schemas import (
    ArtifactProvenance,
    CandidateOutcome,
    DecisionCard,
    ScorerOutcomes,
)

DECISION_CARD_INPUT_SCHEMA_VERSION = "specguard.decision-card-input.v1"
SCORER_OUTCOMES_SCHEMA_VERSION = "specguard.scorer-outcomes.v1"

_ASSAY_CONTEXT_FIELDS = (
    "target",
    "assay_type",
    "assay_id",
    "source",
    "activity_scale",
    "activity_direction",
)
_COMPOUND_DESCRIPTOR_FIELDS = (
    "valid_smiles",
    "canonical_smiles",
    "mw",
    "clogp",
    "tpsa",
    "hbd",
    "hba",
    "rotatable_bonds",
    "heavy_atoms",
)
_SUPPORT_FIELDS = {"id", "smiles", "activity_value", "activity_type", "descriptors"}
_CANDIDATE_FIELDS = {"id", "smiles", "activity_type", "descriptors"}
_CARD_METADATA_FIELDS = (
    "source",
    "assay_id",
    "support_size",
    "candidate_pool_size",
    "seed",
    "selection_policy",
    "feasible_candidate_count",
)
_OUTPUT_SCHEMA_FIELDS = ("rank", "candidate_id", "confidence")


def canonical_json_bytes(payload: Any) -> bytes:
    """Return the canonical JSON encoding used for artifact identity."""

    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return encoded.encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_descriptors(descriptors: dict[str, Any]) -> dict[str, Any]:
    return {key: descriptors[key] for key in _COMPOUND_DESCRIPTOR_FIELDS if key in descriptors}


def system_input_payload(card: DecisionCard) -> dict[str, Any]:
    """Project an evaluator card to the strict fields available to systems.

    Candidate outcomes and unconstrained metadata/extra fields are deliberately
    reconstructed rather than removed from a full model dump. This keeps aliases
    or nested metadata from crossing the scorer boundary accidentally.
    """

    payload: dict[str, Any] = {
        "task_id": card.task_id,
        "assay_context": {key: getattr(card.assay_context, key) for key in _ASSAY_CONTEXT_FIELDS},
        "support_set": [
            {
                "id": compound.id,
                "smiles": compound.smiles,
                "activity_value": compound.activity_value,
                "activity_type": compound.activity_type,
                "descriptors": _project_descriptors(compound.descriptors),
            }
            for compound in card.support_set
        ],
        "candidate_pool": [
            {
                "id": compound.id,
                "smiles": compound.smiles,
                "activity_type": compound.activity_type,
                "descriptors": _project_descriptors(compound.descriptors),
            }
            for compound in card.candidate_pool
        ],
        "budget_k": card.budget_k,
        "hard_constraints": [
            constraint.model_dump(mode="json") for constraint in card.hard_constraints
        ],
        "output_schema": {
            key: card.output_schema[key]
            for key in _OUTPUT_SCHEMA_FIELDS
            if key in card.output_schema
        },
        "metadata": {
            key: card.metadata[key] for key in _CARD_METADATA_FIELDS if key in card.metadata
        },
    }
    if card.schema_version is not None:
        payload["schema_version"] = card.schema_version
    if card.provenance is not None:
        payload["provenance"] = card.provenance.model_dump(mode="json")
    return payload


def split_card_artifacts(
    cards: Iterable[DecisionCard],
    *,
    provenance: ArtifactProvenance,
    input_schema_version: str = DECISION_CARD_INPUT_SCHEMA_VERSION,
    scorer_schema_version: str = SCORER_OUTCOMES_SCHEMA_VERSION,
) -> tuple[list[dict[str, Any]], list[ScorerOutcomes]]:
    """Split evaluator cards into system inputs and scorer-only outcomes."""

    system_inputs: list[dict[str, Any]] = []
    scorer_outcomes: list[ScorerOutcomes] = []
    seen_task_ids: set[str] = set()
    for card in cards:
        if card.task_id in seen_task_ids:
            raise ValueError(f"duplicate decision-card task_id: {card.task_id}")
        seen_task_ids.add(card.task_id)

        missing_outcomes = [
            candidate.id for candidate in card.candidate_pool if candidate.activity_value is None
        ]
        if missing_outcomes:
            raise ValueError(
                f"card {card.task_id} is missing scorer outcomes for: "
                + ", ".join(missing_outcomes[:10])
            )

        release_card = card.model_copy(
            update={"schema_version": input_schema_version, "provenance": provenance}
        )
        input_payload = system_input_payload(release_card)
        outcomes = [
            CandidateOutcome(
                candidate_id=candidate.id,
                activity_value=float(candidate.activity_value),
                activity_type=candidate.activity_type,
            )
            for candidate in card.candidate_pool
        ]
        system_inputs.append(input_payload)
        scorer_outcomes.append(
            ScorerOutcomes(
                schema_version=scorer_schema_version,
                provenance=provenance,
                task_id=card.task_id,
                system_input_sha256=canonical_sha256(input_payload),
                outcomes=outcomes,
            )
        )
    return system_inputs, scorer_outcomes


def write_split_card_artifacts(
    cards: Iterable[DecisionCard],
    system_inputs_path: Path,
    scorer_outcomes_path: Path,
    *,
    provenance: ArtifactProvenance,
    input_schema_version: str = DECISION_CARD_INPUT_SCHEMA_VERSION,
    scorer_schema_version: str = SCORER_OUTCOMES_SCHEMA_VERSION,
) -> tuple[list[dict[str, Any]], list[ScorerOutcomes]]:
    """Write deterministic paired artifacts without timestamps or source paths."""

    system_inputs, scorer_outcomes = split_card_artifacts(
        cards,
        provenance=provenance,
        input_schema_version=input_schema_version,
        scorer_schema_version=scorer_schema_version,
    )
    write_jsonl(system_inputs_path, system_inputs)
    write_jsonl(scorer_outcomes_path, scorer_outcomes)
    return system_inputs, scorer_outcomes


def _validate_system_input_shape(payload: dict[str, Any]) -> None:
    assay_context = payload.get("assay_context")
    if not isinstance(assay_context, dict) or not set(assay_context).issubset(
        _ASSAY_CONTEXT_FIELDS
    ):
        raise ValueError("system input assay_context contains non-public fields")

    card_metadata = payload.get("metadata", {})
    if not isinstance(card_metadata, dict) or not set(card_metadata).issubset(
        _CARD_METADATA_FIELDS
    ):
        raise ValueError("system input metadata contains non-public fields")

    output_schema = payload.get("output_schema", {})
    if not isinstance(output_schema, dict) or not set(output_schema).issubset(
        _OUTPUT_SCHEMA_FIELDS
    ):
        raise ValueError("system input output_schema contains non-public fields")

    for field, allowed_fields in (
        ("support_set", _SUPPORT_FIELDS),
        ("candidate_pool", _CANDIDATE_FIELDS),
    ):
        compounds = payload.get(field)
        if not isinstance(compounds, list):
            raise ValueError(f"system input {field} must be a list")
        for compound in compounds:
            if not isinstance(compound, dict) or not set(compound).issubset(allowed_fields):
                raise ValueError(f"system input {field} contains non-public compound fields")
            descriptors = compound.get("descriptors", {})
            if not isinstance(descriptors, dict) or not set(descriptors).issubset(
                _COMPOUND_DESCRIPTOR_FIELDS
            ):
                raise ValueError(f"system input {field} contains non-public descriptors")


def hydrate_evaluation_cards(
    system_input_rows: Iterable[dict[str, Any]],
    scorer_outcome_rows: Iterable[ScorerOutcomes | dict[str, Any]],
) -> list[DecisionCard]:
    """Validate paired artifacts and restore candidate outcomes for scoring."""

    inputs_by_task: dict[str, tuple[dict[str, Any], DecisionCard]] = {}
    input_order: list[str] = []
    for raw_payload in system_input_rows:
        _validate_system_input_shape(raw_payload)
        card = DecisionCard.model_validate(raw_payload)
        if card.task_id in inputs_by_task:
            raise ValueError(f"duplicate system-input task_id: {card.task_id}")
        if card.schema_version != DECISION_CARD_INPUT_SCHEMA_VERSION or card.provenance is None:
            raise ValueError(f"system input {card.task_id} lacks supported release identity")
        if any(candidate.activity_value is not None for candidate in card.candidate_pool):
            raise ValueError(f"system input {card.task_id} exposes candidate outcomes")
        inputs_by_task[card.task_id] = (raw_payload, card)
        input_order.append(card.task_id)

    outcomes_by_task: dict[str, ScorerOutcomes] = {}
    for raw_outcomes in scorer_outcome_rows:
        outcomes = (
            raw_outcomes
            if isinstance(raw_outcomes, ScorerOutcomes)
            else ScorerOutcomes.model_validate(raw_outcomes)
        )
        if outcomes.task_id in outcomes_by_task:
            raise ValueError(f"duplicate scorer-outcomes task_id: {outcomes.task_id}")
        if outcomes.schema_version != SCORER_OUTCOMES_SCHEMA_VERSION:
            raise ValueError(f"unsupported scorer-outcomes schema: {outcomes.schema_version}")
        outcomes_by_task[outcomes.task_id] = outcomes

    input_tasks = set(inputs_by_task)
    outcome_tasks = set(outcomes_by_task)
    if input_tasks != outcome_tasks:
        missing = sorted(input_tasks - outcome_tasks)
        extra = sorted(outcome_tasks - input_tasks)
        raise ValueError(f"system-input/scorer task mismatch; missing={missing}, extra={extra}")

    hydrated: list[DecisionCard] = []
    for task_id in input_order:
        raw_payload, card = inputs_by_task[task_id]
        outcomes = outcomes_by_task[task_id]
        if canonical_sha256(raw_payload) != outcomes.system_input_sha256:
            raise ValueError(f"system input hash mismatch for task {task_id}")
        if outcomes.provenance != card.provenance:
            raise ValueError(f"system-input/scorer provenance mismatch for task {task_id}")

        candidate_ids = [candidate.id for candidate in card.candidate_pool]
        outcome_ids = [outcome.candidate_id for outcome in outcomes.outcomes]
        if candidate_ids != outcome_ids:
            raise ValueError(f"system-input/scorer candidate mismatch for task {task_id}")

        hydrated_candidates = [
            candidate.model_copy(update={"activity_value": outcome.activity_value})
            for candidate, outcome in zip(card.candidate_pool, outcomes.outcomes, strict=True)
        ]
        hydrated.append(card.model_copy(update={"candidate_pool": hydrated_candidates}))
    return hydrated


def load_evaluation_cards(
    system_inputs_path: Path,
    scorer_outcomes_path: Path | None = None,
) -> list[DecisionCard]:
    """Load legacy monolithic cards or hydrate paired release artifacts."""

    input_rows = read_jsonl(system_inputs_path)
    if scorer_outcomes_path is None:
        return [DecisionCard.model_validate(row) for row in input_rows]
    return hydrate_evaluation_cards(input_rows, read_jsonl(scorer_outcomes_path))


def select_card_by_task_id(cards: list[DecisionCard], task_id: str | None) -> list[DecisionCard]:
    """Return one explicitly selected card, or preserve the full input order."""

    if task_id is None:
        return cards
    selected = [card for card in cards if card.task_id == task_id]
    if not selected:
        raise ValueError(f"task_id {task_id!r} is not present in the decision cards")
    if len(selected) > 1:
        raise ValueError(f"task_id {task_id!r} is duplicated in the decision cards")
    return selected
