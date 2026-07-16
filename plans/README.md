# Plans

> **Historical validity notice (2026-07-16).** Plans and logs are retained as
> an audit trail, but any pre-recovery paper-50 results they mention are invalid
> as scientific evidence. Current release work is governed by
> `active/0030-bounded-v1-archival-release.md` and the corrected artifacts under
> `data/releases/v0.1.0/` and `release/v0.1.0/`. Do not delete or silently
> rewrite older logs; supersede their conclusions explicitly.

Plans are durable execution artifacts. Small changes may use a lightweight
inline plan, but multi-step work must have a checked-in execution plan.

## Directories

- `active/`: work currently being implemented.
- `upcoming/`: approved but not yet active plans.
- `executed/`: completed plans moved from `active/`.
- `logs/`: dated execution logs for completed or interrupted work.
- `templates/`: plan and log templates.
- `tech-debt.md`: known follow-up work that should not be hidden in chat history.

## Lifecycle

1. Create or promote a plan into `active/`.
2. Keep the plan updated while executing.
3. Record commands, tests, decisions, and follow-ups in `logs/`.
4. Move completed plans to `executed/`.
5. Promote the next plan from `upcoming/` when work begins.
