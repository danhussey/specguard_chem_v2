from pathlib import Path

from specguard_chem_v2.io import load_models
from specguard_chem_v2.runner import repair_output, validate_output
from specguard_chem_v2.schemas import DecisionCard, SelectionItem, SystemOutput
from specguard_chem_v2.validation import validate_card_semantics


FIXTURES = Path(__file__).parent / "fixtures"


def test_fixture_cards_validate() -> None:
    cards = load_models(FIXTURES / "cards.jsonl", DecisionCard)
    assert len(cards) == 2
    assert cards[0].budget_k == 3
    assert len(cards[0].candidate_pool) == 5


def test_output_validation_and_repair() -> None:
    card = load_models(FIXTURES / "cards.jsonl", DecisionCard)[0]
    output = SystemOutput(
        task_id=card.task_id,
        system_name="llm_validator",
        selections=[
            SelectionItem(rank=1, candidate_id="A1_C1"),
            SelectionItem(rank=2, candidate_id="A1_C1"),
            SelectionItem(rank=3, candidate_id="NOT_IN_POOL"),
        ],
    )
    issues = validate_output(card, output)
    assert {issue.code for issue in issues} >= {"duplicate", "out_of_pool"}
    repaired = repair_output(card, output)
    repaired_issues = validate_output(card, repaired)
    assert repaired_issues == []
    assert len(repaired.selections) == card.budget_k


def test_card_semantic_validation_passes_fixture() -> None:
    cards = load_models(FIXTURES / "cards.jsonl", DecisionCard)
    assert all(validate_card_semantics(card) == [] for card in cards)
