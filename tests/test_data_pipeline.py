from pathlib import Path
import shutil

from specguard_chem_v2.data.cara import (
    build_cards_from_jsonl,
    inspect_cara_layout,
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
