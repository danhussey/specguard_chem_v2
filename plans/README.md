# Plans

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
