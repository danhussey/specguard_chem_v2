from __future__ import annotations

import pandas as pd
import pytest

from specguard_chem_v2.reports import (
    _card_series_specs,
    _write_paired_bootstrap_tables,
)


def test_best_raw_llm_uses_raw_row_and_raw_metrics(tmp_path) -> None:
    raw_bare = "bare_llm__condition"
    repaired_bare = f"{raw_bare}__posthoc_repair"
    raw_tools = "llm_tools__condition"
    repaired_tools = f"{raw_tools}__posthoc_repair"
    similarity = "similarity_to_best_active"

    frame = pd.DataFrame(
        [
            {
                "system_name": repaired_tools,
                "feasible_utility": 60.0,
                "raw_feasible_utility": 7.0,
                "compliance_rate": 1.0,
            },
            {
                "system_name": raw_tools,
                "feasible_utility": 7.0,
                "raw_feasible_utility": 7.0,
                "compliance_rate": 0.5,
            },
            {
                "system_name": repaired_bare,
                "feasible_utility": 50.0,
                "raw_feasible_utility": 5.0,
                "compliance_rate": 1.0,
            },
            {
                "system_name": raw_bare,
                "feasible_utility": 5.0,
                "raw_feasible_utility": 5.0,
                "compliance_rate": 0.5,
            },
            {
                "system_name": similarity,
                "feasible_utility": 4.0,
                "raw_feasible_utility": None,
                "compliance_rate": 1.0,
            },
        ]
    )
    scores = pd.DataFrame(
        [
            {
                "task_id": task_id,
                "system_name": system_name,
                "feasible_utility": final_utility,
                "raw_feasible_utility": raw_utility,
                "ndcg_at_k": final_ndcg,
                "raw_ndcg_at_k": raw_ndcg,
                "action_validity": final_validity,
                "raw_action_validity": raw_validity,
                "compliance_rate": final_validity,
                "raw_compliance_rate": raw_validity,
            }
            for task_id, offset in (("task-1", 0.0), ("task-2", 2.0))
            for system_name, final_utility, raw_utility, final_ndcg, raw_ndcg, final_validity, raw_validity in (
                (raw_tools, 6.0 + offset, 6.0 + offset, 0.7, 0.7, 0.5, 0.5),
                (repaired_tools, 60.0, 6.0 + offset, 1.0, 0.7, 1.0, 0.5),
                (raw_bare, 5.0, 5.0, 0.6, 0.6, 0.5, 0.5),
                (repaired_bare, 50.0, 5.0, 1.0, 0.6, 1.0, 0.5),
                (similarity, 4.0, None, 0.4, None, 1.0, None),
            )
        ]
    )

    _write_paired_bootstrap_tables(scores, frame, tmp_path)

    key_rows = pd.read_csv(tmp_path / "paired_bootstrap_key_deltas.csv")
    raw_rows = key_rows.loc[key_rows["comparison"] == "best_raw_llm_minus_similarity"].sort_values(
        "metric"
    )
    assert set(raw_rows["system_a"]) == {raw_tools}
    assert set(raw_rows["system_b"]) == {similarity}
    assert set(raw_rows["metric"]) == {
        "raw_action_validity",
        "raw_feasible_utility",
        "raw_ndcg_at_k",
    }
    utility_row = raw_rows.loc[raw_rows["metric"] == "raw_feasible_utility"].iloc[0]
    assert utility_row["mean_delta"] == pytest.approx(3.0)

    best_raw_spec = next(spec for spec in _card_series_specs(frame) if spec[0] == "Best raw LLM")
    assert best_raw_spec == ("Best raw LLM", raw_tools, "raw")
