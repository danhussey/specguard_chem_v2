from __future__ import annotations

import hashlib
import random
from typing import Callable

import numpy as np

from ..chem.constraints import feasible_candidates
from ..chem.descriptors import fingerprint_bits, tanimoto_similarity
from ..schemas import CompoundRecord, DecisionCard, SelectionItem, SystemOutput

DETERMINISTIC_SYSTEMS = {
    "oracle_valid_topk",
    "random_valid",
    "rules_only",
    "similarity_to_best_active",
    "qsar_rf",
    "qsar_gbt",
    "qsar_svm",
}


def _stable_seed(seed: int, task_id: str, system_name: str) -> int:
    digest = hashlib.sha256(f"{seed}:{task_id}:{system_name}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _activity(compound: CompoundRecord) -> float:
    return float(compound.activity_value or 0.0)


def _selection_output(
    card: DecisionCard,
    system_name: str,
    ranked: list[CompoundRecord],
    scores: dict[str, float] | None = None,
) -> SystemOutput:
    selections: list[SelectionItem] = []
    for rank, candidate in enumerate(ranked[: card.budget_k], start=1):
        confidence = None
        if scores and candidate.id in scores:
            raw_score = scores[candidate.id]
            confidence = max(0.0, min(1.0, raw_score))
        selections.append(
            SelectionItem(rank=rank, candidate_id=candidate.id, confidence=confidence)
        )
    return SystemOutput(task_id=card.task_id, system_name=system_name, selections=selections)


def _rank_by_rules(card: DecisionCard) -> tuple[list[CompoundRecord], dict[str, float]]:
    candidates = feasible_candidates(card)
    if not candidates:
        return [], {}

    def desirability(candidate: CompoundRecord) -> float:
        descriptors = candidate.descriptors
        mw = float(descriptors.get("mw") or 0.0)
        clogp = float(descriptors.get("clogp") or 0.0)
        tpsa = float(descriptors.get("tpsa") or 0.0)
        mw_score = max(0.0, 1.0 - abs(mw - 350.0) / 350.0)
        logp_score = max(0.0, 1.0 - abs(clogp - 2.5) / 4.5)
        tpsa_score = max(0.0, 1.0 - abs(tpsa - 75.0) / 150.0)
        return 0.45 * mw_score + 0.35 * logp_score + 0.20 * tpsa_score

    scores = {candidate.id: desirability(candidate) for candidate in candidates}
    ranked = sorted(candidates, key=lambda candidate: (-scores[candidate.id], candidate.id))
    return ranked, scores


def random_valid(card: DecisionCard, *, seed: int = 7) -> SystemOutput:
    rng = random.Random(_stable_seed(seed, card.task_id, "random_valid"))
    candidates = feasible_candidates(card)
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    return _selection_output(card, "random_valid", shuffled)


def rules_only(card: DecisionCard, *, seed: int = 7) -> SystemOutput:
    del seed
    ranked, scores = _rank_by_rules(card)
    return _selection_output(card, "rules_only", ranked, scores)


def similarity_to_best_active(card: DecisionCard, *, seed: int = 7) -> SystemOutput:
    del seed
    if not card.support_set:
        return rules_only(card)
    best_support = max(card.support_set, key=_activity)
    candidates = feasible_candidates(card)
    scores: dict[str, float] = {}
    for candidate in candidates:
        scores[candidate.id] = tanimoto_similarity(best_support.smiles, candidate.smiles) or 0.0
    ranked = sorted(candidates, key=lambda candidate: (-scores[candidate.id], candidate.id))
    return _selection_output(card, "similarity_to_best_active", ranked, scores)


def qsar_rf(card: DecisionCard, *, seed: int = 7) -> SystemOutput:
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError:  # pragma: no cover - dependency is declared in pyproject
        return similarity_to_best_active(card, seed=seed)
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=seed,
        min_samples_leaf=1,
    )
    return _run_qsar_regressor(card, "qsar_rf", model, seed=seed)


def qsar_gbt(card: DecisionCard, *, seed: int = 7) -> SystemOutput:
    try:
        from sklearn.ensemble import GradientBoostingRegressor
    except ImportError:  # pragma: no cover - dependency is declared in pyproject
        return similarity_to_best_active(card, seed=seed)
    model = GradientBoostingRegressor(random_state=seed)
    return _run_qsar_regressor(card, "qsar_gbt", model, seed=seed)


def qsar_svm(card: DecisionCard, *, seed: int = 7) -> SystemOutput:
    del seed
    try:
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVR
    except ImportError:  # pragma: no cover - dependency is declared in pyproject
        return similarity_to_best_active(card)
    model = make_pipeline(StandardScaler(with_mean=False), SVR(kernel="linear", C=1.0))
    return _run_qsar_regressor(card, "qsar_svm", model)


def oracle_valid_topk(card: DecisionCard, *, seed: int = 7) -> SystemOutput:
    del seed
    candidates = feasible_candidates(card)
    ranked = sorted(candidates, key=lambda candidate: (-_activity(candidate), candidate.id))
    return _selection_output(card, "oracle_valid_topk", ranked)


def _run_qsar_regressor(
    card: DecisionCard,
    system_name: str,
    model: object,
    *,
    seed: int = 7,
) -> SystemOutput:
    train = [compound for compound in card.support_set if compound.activity_value is not None]
    candidates = feasible_candidates(card)
    if len(train) < 3 or not candidates:
        fallback = similarity_to_best_active(card, seed=seed)
        return fallback.model_copy(update={"system_name": system_name})

    x_train = np.array([fingerprint_bits(compound.smiles) for compound in train], dtype=np.float32)
    y_train = np.array([float(compound.activity_value) for compound in train], dtype=np.float32)
    x_candidate = np.array(
        [fingerprint_bits(candidate.smiles) for candidate in candidates],
        dtype=np.float32,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_candidate)
    scores = {
        candidate.id: float(prediction)
        for candidate, prediction in zip(candidates, predictions, strict=True)
    }
    ranked = sorted(candidates, key=lambda candidate: (-scores[candidate.id], candidate.id))
    min_score = min(scores.values())
    max_score = max(scores.values())
    confidence_scores = {}
    for candidate_id, score in scores.items():
        if max_score == min_score:
            confidence_scores[candidate_id] = 0.5
        else:
            confidence_scores[candidate_id] = (score - min_score) / (max_score - min_score)
    return _selection_output(card, system_name, ranked, confidence_scores)


BASELINE_RUNNERS: dict[str, Callable[[DecisionCard], SystemOutput]] = {
    "oracle_valid_topk": oracle_valid_topk,
    "random_valid": random_valid,
    "rules_only": rules_only,
    "similarity_to_best_active": similarity_to_best_active,
    "qsar_rf": qsar_rf,
    "qsar_gbt": qsar_gbt,
    "qsar_svm": qsar_svm,
}


def run_baseline_system(card: DecisionCard, system_name: str, *, seed: int = 7) -> SystemOutput:
    if system_name not in BASELINE_RUNNERS:
        raise ValueError(f"Unknown deterministic system: {system_name}")
    return BASELINE_RUNNERS[system_name](card, seed=seed)


def fallback_ranking(card: DecisionCard) -> list[CompoundRecord]:
    ranked, _scores = _rank_by_rules(card)
    return ranked
