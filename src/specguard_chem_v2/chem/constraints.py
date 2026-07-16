from __future__ import annotations

from typing import Iterable

from ..schemas import CompoundRecord, ConstraintSpec, DecisionCard, ValidationIssue
from .descriptors import Chem, compute_descriptors, mol_from_smiles


def default_constraints() -> list[ConstraintSpec]:
    return [
        ConstraintSpec(id="exact_budget", type="output", check="exactly_k"),
        ConstraintSpec(id="candidate_pool_only", type="output", check="in_candidate_pool"),
        ConstraintSpec(id="no_duplicates", type="output", check="no_duplicates"),
        ConstraintSpec(id="exclude_support", type="output", check="exclude_support"),
        ConstraintSpec(
            id="mw_max_500",
            type="candidate",
            check="descriptor_max",
            params={"descriptor": "mw", "max": 500},
        ),
        ConstraintSpec(
            id="clogp_max_4_5",
            type="candidate",
            check="descriptor_max",
            params={"descriptor": "clogp", "max": 4.5},
        ),
        ConstraintSpec(
            id="forbidden_substructures",
            type="candidate",
            check="forbidden_smarts",
            params={"smarts": []},
        ),
    ]


def candidate_constraints(card: DecisionCard) -> list[ConstraintSpec]:
    return [constraint for constraint in card.hard_constraints if constraint.type == "candidate"]


def output_constraints(card: DecisionCard) -> list[ConstraintSpec]:
    return [constraint for constraint in card.hard_constraints if constraint.type == "output"]


def descriptors_for(compound: CompoundRecord) -> dict[str, object]:
    descriptors = dict(compound.descriptors)
    if not descriptors or "valid_smiles" not in descriptors:
        descriptors.update(compute_descriptors(compound.smiles))
    return descriptors


def evaluate_candidate(card: DecisionCard, compound: CompoundRecord) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    descriptors = descriptors_for(compound)
    if descriptors.get("valid_smiles") is False:
        issues.append(
            ValidationIssue(
                code="invalid_smiles",
                message="Candidate SMILES could not be parsed",
                candidate_id=compound.id,
            )
        )
        return issues

    for constraint in candidate_constraints(card):
        if constraint.check == "descriptor_max":
            descriptor = str(constraint.params["descriptor"])
            max_value = float(constraint.params["max"])
            value = descriptors.get(descriptor)
            if value is None or float(value) > max_value:
                issues.append(
                    ValidationIssue(
                        code="descriptor_max",
                        message=f"{descriptor} exceeds max {max_value}",
                        candidate_id=compound.id,
                        constraint_id=constraint.id,
                    )
                )
        elif constraint.check == "descriptor_min":
            descriptor = str(constraint.params["descriptor"])
            min_value = float(constraint.params["min"])
            value = descriptors.get(descriptor)
            if value is None or float(value) < min_value:
                issues.append(
                    ValidationIssue(
                        code="descriptor_min",
                        message=f"{descriptor} below min {min_value}",
                        candidate_id=compound.id,
                        constraint_id=constraint.id,
                    )
                )
        elif constraint.check == "descriptor_range":
            descriptor = str(constraint.params["descriptor"])
            min_value = float(constraint.params["min"])
            max_value = float(constraint.params["max"])
            value = descriptors.get(descriptor)
            if value is None or not (min_value <= float(value) <= max_value):
                issues.append(
                    ValidationIssue(
                        code="descriptor_range",
                        message=f"{descriptor} outside [{min_value}, {max_value}]",
                        candidate_id=compound.id,
                        constraint_id=constraint.id,
                    )
                )
        elif constraint.check == "forbidden_smarts":
            smarts_values = list(constraint.params.get("smarts", []))
            if not smarts_values:
                continue
            mol = mol_from_smiles(compound.smiles)
            if mol is None:
                continue
            for smarts in smarts_values:
                pattern = Chem.MolFromSmarts(str(smarts))
                if pattern is not None and mol.HasSubstructMatch(pattern):
                    issues.append(
                        ValidationIssue(
                            code="forbidden_smarts",
                            message=f"Candidate matches forbidden SMARTS {smarts}",
                            candidate_id=compound.id,
                            constraint_id=constraint.id,
                        )
                    )
        else:
            issues.append(
                ValidationIssue(
                    code="unknown_candidate_constraint",
                    message=f"Unknown candidate constraint check {constraint.check}",
                    candidate_id=compound.id,
                    constraint_id=constraint.id,
                )
            )
    return issues


def is_candidate_feasible(card: DecisionCard, compound: CompoundRecord) -> bool:
    return not evaluate_candidate(card, compound)


def feasible_candidates(card: DecisionCard) -> list[CompoundRecord]:
    return [
        candidate for candidate in card.candidate_pool if is_candidate_feasible(card, candidate)
    ]


def valid_candidate_ids(card: DecisionCard) -> set[str]:
    return {candidate.id for candidate in feasible_candidates(card)}


def filter_feasible(
    card: DecisionCard, compounds: Iterable[CompoundRecord]
) -> list[CompoundRecord]:
    return [compound for compound in compounds if is_candidate_feasible(card, compound)]
