from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL row") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if isinstance(row, BaseModel):
                payload = row.model_dump(mode="json")
            else:
                payload = row
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def load_models(path: Path, model: type[T]) -> list[T]:
    return [model.model_validate(row) for row in read_jsonl(path)]


def dump_models(path: Path, rows: Iterable[BaseModel]) -> None:
    write_jsonl(path, rows)
