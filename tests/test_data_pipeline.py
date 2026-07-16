import shutil
from pathlib import Path

from specguard_chem_v2.data.cara import (
    build_cards_from_jsonl,
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
    cards = build_cards_from_jsonl(records_path, cards_path, target_cards=1, budget_k=3, support_size=3)
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
        "0\tASSAY_A_IC50\tASSAY_A\tMOL_S1\tTARGET_A\tCCO\tIC50\t5.2\tLO\tAll\n"
        "1\tASSAY_A_IC50\tASSAY_A\tMOL_S2\tTARGET_A\tc1ccccc1\tIC50\t6.0\tLO\tAll\n"
        "2\tASSAY_A_IC50\tASSAY_A\tMOL_S3\tTARGET_A\tCC(=O)NC1=CC=CC=C1\tIC50\t6.6\tLO\tAll\n"
        "3\tASSAY_A_IC50\tASSAY_A\tMOL_C1\tTARGET_A\tCC(=O)NC1=CC=CC=C1O\tIC50\t7.4\tLO\tAll\n"
        "4\tASSAY_A_IC50\tASSAY_A\tMOL_C2\tTARGET_A\tc1ccccc1O\tIC50\t6.8\tLO\tAll\n"
        "5\tASSAY_A_IC50\tASSAY_A\tMOL_C3\tTARGET_A\tCCN(CC)CC\tIC50\t5.7\tLO\tAll\n",
        encoding="utf-8",
    )
    (root / "Split" / "LO_All_support.json").write_text('{"ASSAY_A_IC50":[0,1,2]}', encoding="utf-8")
    (root / "Split" / "LO_All_query.json").write_text('{"ASSAY_A_IC50":[3,4,5]}', encoding="utf-8")

    records = import_official_cara_records(tmp_path / "raw", split_name="LO_All")
    assert len(records) == 6
    assert {record["role"] for record in records} == {"support", "candidate"}
    assert records[0]["assay_id"] == "ASSAY_A_IC50"
    assert records[0]["target"] == "TARGET_A"
