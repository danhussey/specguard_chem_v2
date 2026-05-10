# 2026-05-10 0005 LLM Agent Systems

## Summary

Completed offline-first LLM system hardening. LLM requests now include explicit
condition metadata, chat messages are generated through a single helper, and the
CLI can export provider-ready request/message payloads before any live call.

## Commands Run

```bash
uv run --extra dev pytest
uv run sgchem export-llm-requests tests/fixtures/cards.jsonl --systems bare_llm,llm_tools --out /tmp/sgchem_llm_requests.jsonl
uv run sgchem run-suite tests/fixtures/cards.jsonl --systems bare_llm,llm_validator,llm_tools,llm_tools_validator --cache-dir tests/fixtures/llm_cache --out runs/fixture_llm
```

## Tests

Final result:

```text
12 passed
```

## Files Changed

- `src/specguard_chem_v2/systems/llm.py`
- `src/specguard_chem_v2/cli.py`
- `docs/LLM_SYSTEMS.md`
- `docs/EXPERIMENT_PROTOCOL.md`
- `docs/RUNBOOK.md`
- `tests/test_runner_scoring_reports.py`
- `tests/test_cli.py`

## Decisions

- Keep live provider calls opt-in only.
- Export exact chat messages for review before live execution.
- Keep stable task-level cache fixture names for tests and review packets.

## Follow-Up Work

- Add real-card LLM request exports when paper card selection is frozen.
- In `0005`, produce paper-facing tables and plots from committed/reproducible
  run commands.
