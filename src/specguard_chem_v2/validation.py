from __future__ import annotations

from .chem.constraints import feasible_candidates
from .schemas import DecisionCard, ValidationIssue


def validate_card_semantics(card: DecisionCard) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if len(feasible_candidates(card)) < card.budget_k:
        issues.append(
            ValidationIssue(
                code="insufficient_feasible_candidates",
                message="Fewer feasible candidates than budget_k after hard constraints",
            )
        )
    support_ids = card.support_ids
    candidate_ids = set(card.candidate_by_id)
    overlap = sorted(support_ids & candidate_ids)
    for candidate_id in overlap:
        issues.append(
            ValidationIssue(
                code="support_candidate_overlap",
                message="A candidate ID also appears in the support set",
                candidate_id=candidate_id,
            )
        )
    missing_activity = [
        candidate.id for candidate in card.candidate_pool if candidate.activity_value is None
    ]
    for candidate_id in missing_activity:
        issues.append(
            ValidationIssue(
                code="missing_candidate_activity",
                message="Candidate is missing hidden activity for scoring",
                candidate_id=candidate_id,
            )
        )
    return issues
