# Decisions

## 2026-05-10: Build v2 as a clean repository

Decision: implement `specguard_chem_v2` as a clean package in the empty workspace.

Reason: the sibling `../specguard-chem` project is a mature compliance benchmark.
The MD project has a different unit of evaluation: finite-budget constrained
candidate prioritisation.

## 2026-05-10: Use a plans directory as a first-class execution record

Decision: use `plans/active`, `plans/upcoming`, `plans/executed`, and
`plans/logs` rather than a single implementation plan document.

Reason: future agent chats need durable context, progress logs, and decision
history without relying on conversation memory.
