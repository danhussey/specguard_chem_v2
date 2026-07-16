import shutil
from pathlib import Path

import pytest

from specguard_chem_v2.artifacts import load_evaluation_cards
from specguard_chem_v2.data.cara import (
    build_cards_from_jsonl,
    build_decision_cards,
    import_official_cara_records,
    inspect_cara_layout,
    summarize_cards,
    write_imported_records,
)
from specguard_chem_v2.io import load_models
from specguard_chem_v2.schemas import DecisionCard

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_and_build_cards_from_cara_like_fixture(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    shutil.copy(FIXTURES / "cara_like.csv", source_dir / "cara_like.csv")
    records_path = tmp_path / "records.jsonl"
    records = write_imported_records(source_dir, records_path)
    assert len(records) == 16

    cards_path = tmp_path / "cards.jsonl"
    cards = build_cards_from_jsonl(
        records_path,
        cards_path,
        target_cards=2,
        budget_k=3,
        support_size=3,
    )
    assert len(cards) == 2
    loaded = load_models(cards_path, DecisionCard)
    assert [card.task_id for card in loaded] == [card.task_id for card in cards]

    second_cards_path = tmp_path / "second" / "cards.jsonl"
    build_cards_from_jsonl(
        records_path,
        second_cards_path,
        target_cards=2,
        budget_k=3,
        support_size=3,
    )
    assert cards_path.read_bytes() == second_cards_path.read_bytes()
    assert (
        cards_path.with_suffix(".meta.json").read_bytes()
        == second_cards_path.with_suffix(".meta.json").read_bytes()
    )
    assert (
        cards_path.with_suffix(".audit.json").read_bytes()
        == second_cards_path.with_suffix(".audit.json").read_bytes()
    )


def test_build_split_release_cards_redacts_and_hydrates(tmp_path: Path) -> None:
    records_path = tmp_path / "records.jsonl"
    write_imported_records(FIXTURES / "cara_split_layout", records_path)
    system_inputs_path = tmp_path / "system_input_cards.jsonl"
    scorer_outcomes_path = tmp_path / "scorer_outcomes.jsonl"

    cards = build_cards_from_jsonl(
        records_path,
        system_inputs_path,
        scorer_outcomes_out=scorer_outcomes_path,
        benchmark_version="0.1.0-rc.1",
        data_version="cara-lo-all/0.1.0-rc.1",
        target_cards=1,
        budget_k=3,
        support_size=3,
    )

    assert (
        b'"activity_value"'
        not in system_inputs_path.read_bytes()
        .split(b'"candidate_pool":', maxsplit=1)[1]
        .split(b'"hard_constraints":', maxsplit=1)[0]
    )
    hydrated = load_evaluation_cards(system_inputs_path, scorer_outcomes_path)
    assert [candidate.activity_value for candidate in hydrated[0].candidate_pool] == [
        candidate.activity_value for candidate in cards[0].candidate_pool
    ]

    with pytest.raises(ValueError, match="benchmark_version and data_version"):
        build_cards_from_jsonl(
            records_path,
            tmp_path / "invalid.jsonl",
            scorer_outcomes_out=tmp_path / "invalid-outcomes.jsonl",
        )


def test_import_support_query_split_layout(tmp_path: Path) -> None:
    records_path = tmp_path / "records.jsonl"
    source = FIXTURES / "cara_split_layout"
    records = write_imported_records(source, records_path)
    assert {record["role"] for record in records} == {"support", "candidate"}
    assert {record["assay_id"] for record in records} == {"assay_alpha"}

    layout = inspect_cara_layout(source)
    assert len(layout["tables"]) == 2
    assert {table["role_hint"] for table in layout["tables"]} == {"support", "candidate"}

    cards_path = tmp_path / "cards.jsonl"
    cards = build_cards_from_jsonl(
        records_path, cards_path, target_cards=1, budget_k=3, support_size=3
    )
    assert len(cards) == 1
    assert cards[0].metadata["feasible_candidate_count"] >= 3
    summary = summarize_cards(cards)
    assert summary["num_cards"] == 1
    assert summary["feasible_candidate_count"]["min"] >= 3


def test_import_official_cara_split_layout(tmp_path: Path) -> None:
    root = tmp_path / "raw" / "extracted" / "CARA"
    (root / "Task").mkdir(parents=True)
    (root / "Split").mkdir()
    (root / "Task" / "LO_All.tsv").write_text(
        "\tTask ID\tAssay ChEMBL ID\tMolecule ChEMBL ID\tTarget ChEMBL ID\tSmiles\tValue Type\tpChEMBL Value\tTask Type\tTarget Type\n"
        "100\tASSAY_A_IC50\tASSAY_A\tMOL_S1\tTARGET_A\tCCO\tIC50\t5.2\tLO\tAll\n"
        "101\tASSAY_A_IC50\tASSAY_A\tMOL_S2\tTARGET_A\tc1ccccc1\tIC50\t6.0\tLO\tAll\n"
        "102\tASSAY_A_IC50\tASSAY_A\tMOL_S3\tTARGET_A\tCC(=O)NC1=CC=CC=C1\tIC50\t6.6\tLO\tAll\n"
        "103\tASSAY_A_IC50\tASSAY_A\tMOL_C1\tTARGET_A\tCC(=O)NC1=CC=CC=C1O\tIC50\t7.4\tLO\tAll\n"
        "104\tASSAY_A_IC50\tASSAY_A\tMOL_C2\tTARGET_A\tc1ccccc1O\tIC50\t6.8\tLO\tAll\n"
        "105\tASSAY_A_IC50\tASSAY_A\tMOL_C3\tTARGET_A\tCCN(CC)CC\tIC50\t5.7\tLO\tAll\n",
        encoding="utf-8",
    )
    (root / "Split" / "LO_All_support.json").write_text(
        '{"ASSAY_A_IC50":[0,1,2]}', encoding="utf-8"
    )
    (root / "Split" / "LO_All_query.json").write_text('{"ASSAY_A_IC50":[3,4,5]}', encoding="utf-8")

    records = import_official_cara_records(tmp_path / "raw", split_name="LO_All")
    assert len(records) == 6
    assert {record["role"] for record in records} == {"support", "candidate"}
    assert records[0]["assay_id"] == "ASSAY_A_IC50"
    assert records[0]["target"] == "TARGET_A"
    assert records[0]["source_file"] == "Task/LO_All.tsv"
    assert {record["activity_type"] for record in records} == {"pChEMBL"}
    assert [record["compound_id"] for record in records] == [
        "MOL_S1",
        "MOL_S2",
        "MOL_S3",
        "MOL_C1",
        "MOL_C2",
        "MOL_C3",
    ]
    assert [record["row_index"] for record in records] == list(range(6))

    cards = build_decision_cards(records, target_cards=1, budget_k=3, support_size=3)
    assert cards[0].assay_context.target == "TARGET_A"
    assert cards[0].assay_context.assay_type == "IC50"
    assert cards[0].assay_context.activity_scale == "pChEMBL"
    assert cards[0].assay_context.activity_direction == "higher_is_better"
    assert {compound.activity_type for compound in cards[0].support_set} == {"pChEMBL"}
    assert {compound.activity_type for compound in cards[0].candidate_pool} == {"pChEMBL"}


def test_import_official_cara_rejects_task_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "raw" / "extracted" / "CARA"
    (root / "Task").mkdir(parents=True)
    (root / "Split").mkdir()
    (root / "Task" / "LO_All.tsv").write_text(
        "Task ID\tMolecule ChEMBL ID\tSmiles\tpChEMBL Value\nASSAY_B\tMOL_1\tCCO\t5.2\n",
        encoding="utf-8",
    )
    (root / "Split" / "LO_All_support.json").write_text('{"ASSAY_A":[0]}', encoding="utf-8")
    (root / "Split" / "LO_All_query.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="split/task mismatch"):
        import_official_cara_records(tmp_path / "raw", split_name="LO_All")


def test_import_official_cara_rejects_out_of_range_position(tmp_path: Path) -> None:
    root = tmp_path / "raw" / "extracted" / "CARA"
    (root / "Task").mkdir(parents=True)
    (root / "Split").mkdir()
    (root / "Task" / "LO_All.tsv").write_text(
        "Task ID\tMolecule ChEMBL ID\tSmiles\tpChEMBL Value\nASSAY_A\tMOL_1\tCCO\t5.2\n",
        encoding="utf-8",
    )
    (root / "Split" / "LO_All_support.json").write_text('{"ASSAY_A":[1]}', encoding="utf-8")
    (root / "Split" / "LO_All_query.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="out of range"):
        import_official_cara_records(tmp_path / "raw", split_name="LO_All")


def test_build_cards_rejects_duplicate_candidate_ids() -> None:
    support = [
        {
            "assay_id": "ASSAY_A",
            "compound_id": f"S{index}",
            "smiles": "CCO",
            "activity_value": 5.0 + index,
            "role": "support",
        }
        for index in range(3)
    ]
    candidates = [
        {
            "assay_id": "ASSAY_A",
            "compound_id": "DUPLICATE",
            "smiles": "CCN",
            "activity_value": 6.0 + index,
            "role": "candidate",
        }
        for index in range(2)
    ]

    with pytest.raises(ValueError, match="Duplicate candidate compound ID"):
        build_decision_cards(
            support + candidates,
            target_cards=1,
            budget_k=1,
            support_size=3,
        )
