from __future__ import annotations

import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from specguard_chem_v2.artifacts import (
    DECISION_CARD_INPUT_SCHEMA_VERSION,
    SCORER_OUTCOMES_SCHEMA_VERSION,
    canonical_sha256,
    hydrate_evaluation_cards,
    load_evaluation_cards,
    split_card_artifacts,
    system_input_payload,
    write_split_card_artifacts,
)
from specguard_chem_v2.io import load_models
from specguard_chem_v2.runner import run_system_file
from specguard_chem_v2.schemas import (
    ArtifactProvenance,
    CardScore,
    DecisionCard,
    RunRecord,
    ScorerOutcomes,
)
from specguard_chem_v2.scoring import score_run
from specguard_chem_v2.systems.llm import build_llm_request

FIXTURES = Path(__file__).parent / "fixtures"


def _provenance(*, source: str = "a", config: str = "b") -> ArtifactProvenance:
    return ArtifactProvenance(
        benchmark_version="0.1.0",
        data_version="cara-lo/0.1.0",
        source_sha256=source * 64,
        config_sha256=config * 64,
    )


def _fixture_cards() -> list[DecisionCard]:
    return load_models(FIXTURES / "cards.jsonl", DecisionCard)


def test_legacy_decision_cards_remain_loadable() -> None:
    cards = _fixture_cards()
    assert cards[0].schema_version is None
    assert cards[0].provenance is None
    assert load_evaluation_cards(FIXTURES / "cards.jsonl") == cards


def test_split_artifacts_redact_and_round_trip_outcomes() -> None:
    cards = _fixture_cards()
    inputs, outcomes = split_card_artifacts(cards, provenance=_provenance())

    assert inputs[0]["schema_version"] == DECISION_CARD_INPUT_SCHEMA_VERSION
    assert outcomes[0].schema_version == SCORER_OUTCOMES_SCHEMA_VERSION
    assert outcomes[0].system_input_sha256 == canonical_sha256(inputs[0])
    assert all("activity_value" not in candidate for candidate in inputs[0]["candidate_pool"])
    assert all("activity_value" in support for support in inputs[0]["support_set"])

    hydrated = hydrate_evaluation_cards(inputs, outcomes)
    for original, restored in zip(cards, hydrated, strict=True):
        assert [candidate.activity_value for candidate in restored.candidate_pool] == [
            candidate.activity_value for candidate in original.candidate_pool
        ]

    release_request = build_llm_request(DecisionCard.model_validate(inputs[0]), "bare_llm")
    assert release_request["artifact_provenance"] == _provenance().model_dump(mode="json")
    assert release_request["system_input_sha256"] == outcomes[0].system_input_sha256
    assert "artifact_provenance" not in build_llm_request(cards[0], "bare_llm")


def test_system_projection_is_an_allowlist_not_a_shallow_redaction() -> None:
    card = _fixture_cards()[0]
    candidate = card.candidate_pool[0]
    dirty_candidate = candidate.model_copy(
        update={
            "pIC50": 99.0,
            "metadata": {"activity_value": 99.0, "source_file": "/private/tmp/source.tsv"},
            "descriptors": {**candidate.descriptors, "activity_value": 99.0},
        }
    )
    dirty = card.model_copy(
        update={
            "candidate_pool": [dirty_candidate, *card.candidate_pool[1:]],
            "metadata": {**card.metadata, "generated_at": "now", "records_path": "/tmp/data"},
            "assay_context": card.assay_context.model_copy(update={"hidden_outcome": 99.0}),
        }
    )

    candidate_payload = system_input_payload(dirty)["candidate_pool"][0]
    assert set(candidate_payload) == {"id", "smiles", "activity_type", "descriptors"}
    assert "activity_value" not in candidate_payload["descriptors"]
    assert "generated_at" not in system_input_payload(dirty)["metadata"]
    assert "hidden_outcome" not in system_input_payload(dirty)["assay_context"]


def test_split_artifact_bytes_are_independent_of_output_path(tmp_path: Path) -> None:
    cards = _fixture_cards()
    first = tmp_path / "one"
    second = tmp_path / "two"
    write_split_card_artifacts(
        cards,
        first / "inputs.jsonl",
        first / "outcomes.jsonl",
        provenance=_provenance(),
    )
    write_split_card_artifacts(
        cards,
        second / "inputs.jsonl",
        second / "outcomes.jsonl",
        provenance=_provenance(),
    )

    assert (first / "inputs.jsonl").read_bytes() == (second / "inputs.jsonl").read_bytes()
    assert (first / "outcomes.jsonl").read_bytes() == (second / "outcomes.jsonl").read_bytes()
    assert b"generated_at" not in (first / "inputs.jsonl").read_bytes()
    assert b"/private/" not in (first / "inputs.jsonl").read_bytes()


def test_hydration_rejects_hash_and_provenance_mismatches() -> None:
    inputs, outcomes = split_card_artifacts(_fixture_cards(), provenance=_provenance())
    tampered_inputs = copy.deepcopy(inputs)
    tampered_inputs[0]["budget_k"] = 2
    with pytest.raises(ValueError, match="hash mismatch"):
        hydrate_evaluation_cards(tampered_inputs, outcomes)

    mismatched_outcomes = list(outcomes)
    mismatched_outcomes[0] = outcomes[0].model_copy(update={"provenance": _provenance(source="c")})
    with pytest.raises(ValueError, match="provenance mismatch"):
        hydrate_evaluation_cards(inputs, mismatched_outcomes)


def test_hydration_rejects_task_candidate_and_public_shape_mismatches() -> None:
    inputs, outcomes = split_card_artifacts(_fixture_cards(), provenance=_provenance())
    with pytest.raises(ValueError, match="task mismatch"):
        hydrate_evaluation_cards(inputs, outcomes[:-1])

    missing_candidate = ScorerOutcomes.model_validate(
        {
            **outcomes[0].model_dump(mode="json"),
            "outcomes": [outcome.model_dump(mode="json") for outcome in outcomes[0].outcomes[:-1]],
        }
    )
    with pytest.raises(ValueError, match="candidate mismatch"):
        hydrate_evaluation_cards(inputs[:1], [missing_candidate])

    leaky_inputs = copy.deepcopy(inputs[:1])
    leaky_inputs[0]["candidate_pool"][0]["activity_value"] = 9.9
    with pytest.raises(ValueError, match="non-public compound fields"):
        hydrate_evaluation_cards(leaky_inputs, outcomes[:1])


def test_scorer_outcome_ids_and_release_identity_are_strict() -> None:
    inputs, outcomes = split_card_artifacts(_fixture_cards()[:1], provenance=_provenance())
    duplicate = outcomes[0].model_dump(mode="json")
    duplicate["outcomes"].append(dict(duplicate["outcomes"][0]))
    with pytest.raises(ValidationError, match="candidate IDs must be unique"):
        ScorerOutcomes.model_validate(duplicate)

    half_versioned = inputs[0].copy()
    half_versioned.pop("provenance")
    with pytest.raises(ValidationError, match="must either both be present"):
        DecisionCard.model_validate(half_versioned)


def test_split_runner_and_scoring_match_legacy_cards(tmp_path: Path) -> None:
    legacy_cards = FIXTURES / "cards.jsonl"
    inputs_path = tmp_path / "system_inputs.jsonl"
    outcomes_path = tmp_path / "scorer_outcomes.jsonl"
    write_split_card_artifacts(
        _fixture_cards(),
        inputs_path,
        outcomes_path,
        provenance=_provenance(),
    )

    legacy_trace = tmp_path / "legacy" / "trace.jsonl"
    split_trace = tmp_path / "split" / "trace.jsonl"
    run_system_file(legacy_cards, "rules_only", legacy_trace)
    run_system_file(
        inputs_path,
        "rules_only",
        split_trace,
        scorer_outcomes_path=outcomes_path,
    )
    legacy_records = load_models(legacy_trace, RunRecord)
    split_records = load_models(split_trace, RunRecord)
    assert [record.output.selections for record in split_records] == [
        record.output.selections for record in legacy_records
    ]

    legacy_scores = score_run(legacy_cards, legacy_trace, tmp_path / "legacy-scores")
    split_scores = score_run(
        inputs_path,
        split_trace,
        tmp_path / "split-scores",
        scorer_outcomes_path=outcomes_path,
    )
    assert [score.model_dump(mode="json") for score in split_scores] == [
        score.model_dump(mode="json") for score in legacy_scores
    ]
    assert load_models(tmp_path / "split-scores" / "card_scores.jsonl", CardScore)

    with pytest.raises(ValueError, match="scoring requires candidate outcomes"):
        score_run(inputs_path, split_trace, tmp_path / "missing-outcomes")


def test_split_oracle_requires_scorer_outcomes(tmp_path: Path) -> None:
    inputs_path = tmp_path / "system_inputs.jsonl"
    outcomes_path = tmp_path / "scorer_outcomes.jsonl"
    write_split_card_artifacts(
        _fixture_cards(),
        inputs_path,
        outcomes_path,
        provenance=_provenance(),
    )

    with pytest.raises(ValueError, match="oracle_valid_topk requires scorer outcomes"):
        run_system_file(inputs_path, "oracle_valid_topk", tmp_path / "invalid.jsonl")

    records = run_system_file(
        inputs_path,
        "oracle_valid_topk",
        tmp_path / "oracle.jsonl",
        scorer_outcomes_path=outcomes_path,
    )
    assert len(records) == len(_fixture_cards())
