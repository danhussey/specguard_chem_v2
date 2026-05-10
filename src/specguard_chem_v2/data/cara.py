from __future__ import annotations

import hashlib
import json
import re
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ..chem.constraints import default_constraints, feasible_candidates
from ..chem.descriptors import compute_descriptors
from ..io import ensure_parent, read_jsonl, write_json, write_jsonl
from ..schemas import AssayContext, CompoundRecord, ConstraintSpec, DecisionCard

DEFAULT_CARA_URL = "https://zenodo.org/records/14740896/files/CARA.zip?download=1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract_zip(archive_path: Path, extracted_dir: Path) -> None:
    extracted_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        root = extracted_dir.resolve()
        for member in archive.infolist():
            destination = (extracted_dir / member.filename).resolve()
            if root not in destination.parents and destination != root:
                raise ValueError(f"Unsafe archive member path: {member.filename}")
            archive.extract(member, extracted_dir)


def _expected_total_from_headers(headers: Any, *, bytes_before_request: int) -> int | None:
    content_range = headers.get("Content-Range")
    if content_range:
        match = re.search(r"/(\d+)$", content_range)
        if match:
            return int(match.group(1))
    content_length = headers.get("Content-Length")
    if content_length is None:
        return None
    return bytes_before_request + int(content_length)


def _download_with_resume(
    *,
    url: str,
    partial_path: Path,
    max_attempts: int,
) -> tuple[int, int | None, int]:
    expected_bytes: int | None = None
    attempts_used = 0
    for attempt in range(1, max_attempts + 1):
        attempts_used = attempt
        existing_bytes = partial_path.stat().st_size if partial_path.exists() else 0
        headers = {"User-Agent": "specguard-chem-v2/0.1"}
        if existing_bytes:
            headers["Range"] = f"bytes={existing_bytes}-"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            if existing_bytes and getattr(response, "status", None) != 206:
                existing_bytes = 0
                partial_path.unlink(missing_ok=True)
            expected_bytes = _expected_total_from_headers(
                response.headers,
                bytes_before_request=existing_bytes,
            )
            mode = "ab" if existing_bytes else "wb"
            with partial_path.open(mode) as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
        bytes_written = partial_path.stat().st_size if partial_path.exists() else 0
        if expected_bytes is not None and bytes_written >= expected_bytes:
            return bytes_written, expected_bytes, attempts_used
    return partial_path.stat().st_size if partial_path.exists() else 0, expected_bytes, attempts_used


def download_cara(
    out_dir: Path,
    url: str = DEFAULT_CARA_URL,
    *,
    max_attempts: int = 8,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / "CARA.zip"
    partial_path = archive_path.with_suffix(".zip.part")
    bytes_written, expected_bytes, attempts_used = _download_with_resume(
        url=url,
        partial_path=partial_path,
        max_attempts=max_attempts,
    )
    if expected_bytes is not None and bytes_written != expected_bytes:
        raise RuntimeError(
            f"Incomplete CARA download: wrote {bytes_written} bytes, expected {expected_bytes}. "
            f"Partial file kept at {partial_path}; rerun download-cara to resume."
        )
    partial_path.replace(archive_path)

    extracted_dir = out_dir / "extracted"
    if not zipfile.is_zipfile(archive_path):
        raise RuntimeError(f"Downloaded CARA archive is not a valid zip file: {archive_path}")
    _safe_extract_zip(archive_path, extracted_dir)

    provenance = {
        "source_url": url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "archive_path": str(archive_path),
        "archive_sha256": sha256_file(archive_path),
        "archive_bytes": archive_path.stat().st_size,
        "expected_bytes": expected_bytes,
        "download_attempts": attempts_used,
        "extracted_dir": str(extracted_dir) if extracted_dir.exists() else None,
    }
    write_json(out_dir / "provenance.json", provenance)
    return provenance


def _read_json_table(path: Path) -> pd.DataFrame | None:
    try:
        if path.suffix.lower() == ".jsonl":
            rows = read_jsonl(path)
            return pd.DataFrame(rows)
        frame = pd.read_json(path)
        if isinstance(frame, pd.Series):
            return pd.DataFrame(frame.tolist())
        return frame
    except Exception:
        return None


def _read_table(path: Path) -> pd.DataFrame | None:
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in {".tsv", ".txt"}:
            return pd.read_csv(path, sep="\t")
        if suffix == ".parquet":
            return pd.read_parquet(path)
        if suffix in {".json", ".jsonl"}:
            return _read_json_table(path)
    except Exception:
        return None
    return None


def _find_column(columns: Iterable[str], aliases: Iterable[str]) -> str | None:
    normalized = {column.lower().strip(): column for column in columns}
    for alias in aliases:
        if alias.lower() in normalized:
            return normalized[alias.lower()]
    for column in columns:
        lowered = column.lower()
        for alias in aliases:
            if alias.lower() in lowered:
                return column
    return None


def _role_from_value(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    lowered = str(value).strip().lower()
    if lowered in {"support", "train", "shot", "fewshot", "few_shot"}:
        return "support"
    if lowered in {"query", "candidate", "candidates", "test", "valid", "validation"}:
        return "candidate"
    return None


def _role_from_path(path: Path) -> str | None:
    parts = [part.lower() for part in path.parts]
    label = " ".join(parts)
    if any(token in label for token in ["support", "fewshot", "few_shot", "finetune"]):
        return "support"
    if any(token in label for token in ["query", "candidate", "candidates"]):
        return "candidate"
    return None


def _assay_id_from_path(path: Path) -> str:
    stem = path.stem.lower()
    if stem in {"support", "query", "candidate", "candidates", "train", "test", "valid"}:
        return path.parent.name
    return path.stem


def _task_kind_from_path(path: Path) -> str | None:
    label = "/".join(part.lower() for part in path.parts)
    if "lo" in label or "lead" in label:
        return "LO"
    if "vs" in label or "screen" in label:
        return "VS"
    return None


def _candidate_record_from_row(
    row: pd.Series,
    columns: dict[str, str | None],
    source: Path,
) -> dict[str, Any] | None:
    smiles_col = columns["smiles"]
    activity_col = columns["activity"]
    if smiles_col is None or activity_col is None:
        return None
    smiles = row.get(smiles_col)
    activity = row.get(activity_col)
    if pd.isna(smiles) or pd.isna(activity):
        return None
    compound_col = columns["compound_id"]
    assay_col = columns["assay_id"]
    split_col = columns["split"]
    target_col = columns.get("target")
    assay_id = row.get(assay_col) if assay_col else _assay_id_from_path(source)
    compound_id = row.get(compound_col) if compound_col else f"{source.stem}_{int(row.name):06d}"
    role = _role_from_value(row.get(split_col)) if split_col else None
    role = role or _role_from_path(source)
    try:
        activity_value = float(activity)
    except (TypeError, ValueError):
        return None
    return {
        "assay_id": str(assay_id),
        "compound_id": str(compound_id),
        "smiles": str(smiles),
        "activity_value": activity_value,
        "role": role,
        "target": str(row.get(target_col)) if target_col and not pd.isna(row.get(target_col)) else None,
        "task_kind": _task_kind_from_path(source),
        "source_file": str(source),
    }


def _find_official_cara_root(raw_dir: Path) -> Path | None:
    candidates = [
        raw_dir / "CARA",
        raw_dir / "extracted" / "CARA",
    ]
    for candidate in candidates:
        if (candidate / "Task").exists() and (candidate / "Split").exists():
            return candidate
    for candidate in raw_dir.rglob("CARA"):
        if (candidate / "Task").exists() and (candidate / "Split").exists():
            return candidate
    return None


def _official_task_table(root: Path, split_name: str) -> Path | None:
    path = root / "Task" / f"{split_name}.tsv"
    return path if path.exists() else None


def _official_split_file(root: Path, split_name: str, role: str) -> Path | None:
    suffix = "support" if role == "support" else "query"
    path = root / "Split" / f"{split_name}_{suffix}.json"
    return path if path.exists() else None


def _load_split_indices(path: Path) -> dict[str, list[int]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    result: dict[str, list[int]] = {}
    for task_id, indices in payload.items():
        if not isinstance(indices, list):
            continue
        result[str(task_id)] = [int(index) for index in indices]
    return result


def _row_lookup(frame: pd.DataFrame) -> pd.DataFrame:
    if "Unnamed: 0" not in frame.columns:
        return frame
    indexed = frame.set_index("Unnamed: 0", drop=False)
    indexed.index = indexed.index.astype(int)
    return indexed


def _record_from_official_row(
    *,
    row: pd.Series,
    assay_id: str,
    role: str,
    source_file: Path,
    row_index: int,
    split_name: str,
) -> dict[str, Any] | None:
    smiles = row.get("Smiles")
    activity = row.get("pChEMBL Value")
    if pd.isna(smiles) or pd.isna(activity):
        return None
    try:
        activity_value = float(activity)
    except (TypeError, ValueError):
        return None
    molecule_id = row.get("Molecule ChEMBL ID")
    compound_id = str(molecule_id) if not pd.isna(molecule_id) else f"{assay_id}_{row_index}"
    return {
        "assay_id": assay_id,
        "compound_id": compound_id,
        "smiles": str(smiles),
        "activity_value": activity_value,
        "role": role,
        "target": str(row.get("Target ChEMBL ID")) if not pd.isna(row.get("Target ChEMBL ID")) else None,
        "task_kind": str(row.get("Task Type")) if not pd.isna(row.get("Task Type")) else None,
        "assay_chembl_id": str(row.get("Assay ChEMBL ID"))
        if not pd.isna(row.get("Assay ChEMBL ID"))
        else None,
        "value_type": str(row.get("Value Type")) if not pd.isna(row.get("Value Type")) else None,
        "target_type": str(row.get("Target Type")) if not pd.isna(row.get("Target Type")) else None,
        "source_file": str(source_file),
        "source_split": split_name,
        "row_index": row_index,
    }


def import_official_cara_records(raw_dir: Path, *, split_name: str = "LO_All") -> list[dict[str, Any]]:
    root = _find_official_cara_root(raw_dir)
    if root is None:
        return []
    task_path = _official_task_table(root, split_name)
    support_path = _official_split_file(root, split_name, "support")
    query_path = _official_split_file(root, split_name, "candidate")
    if task_path is None or support_path is None or query_path is None:
        return []

    frame = _row_lookup(pd.read_csv(task_path, sep="\t"))
    role_files = {
        "support": support_path,
        "candidate": query_path,
    }
    records: list[dict[str, Any]] = []
    for role, split_path in role_files.items():
        split_indices = _load_split_indices(split_path)
        for assay_id, indices in sorted(split_indices.items()):
            for row_index in indices:
                if row_index not in frame.index:
                    continue
                record = _record_from_official_row(
                    row=frame.loc[row_index],
                    assay_id=assay_id,
                    role=role,
                    source_file=task_path,
                    row_index=row_index,
                    split_name=split_name,
                )
                if record is not None:
                    records.append(record)
    return records


def inspect_cara_layout(raw_dir: Path) -> dict[str, Any]:
    roots = [raw_dir]
    extracted = raw_dir / "extracted"
    if extracted.exists():
        roots.insert(0, extracted)

    table_summaries: list[dict[str, Any]] = []
    suffix_counts: dict[str, int] = defaultdict(int)
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            suffix_counts[path.suffix.lower() or "<none>"] += 1
            if path.suffix.lower() not in {".csv", ".tsv", ".txt", ".parquet", ".json", ".jsonl"}:
                continue
            frame = _read_table(path)
            if frame is None:
                json_keys = None
                if path.suffix.lower() == ".json":
                    try:
                        with path.open("r", encoding="utf-8") as handle:
                            payload = json.load(handle)
                        if isinstance(payload, dict):
                            json_keys = list(payload.keys())[:40]
                    except Exception:
                        json_keys = None
                table_summaries.append(
                    {
                        "path": str(path),
                        "readable": False,
                        "json_keys": json_keys,
                        "role_hint": _role_from_path(path),
                        "task_kind_hint": _task_kind_from_path(path),
                    }
                )
                continue
            table_summaries.append(
                {
                    "path": str(path),
                    "readable": True,
                    "rows": int(len(frame)),
                    "columns": [str(column) for column in frame.columns[:40]],
                    "role_hint": _role_from_path(path),
                    "task_kind_hint": _task_kind_from_path(path),
                }
            )
    return {
        "raw_dir": str(raw_dir),
        "inspected_at": datetime.now(timezone.utc).isoformat(),
        "suffix_counts": dict(sorted(suffix_counts.items())),
        "tables": table_summaries,
    }


def import_cara_records(raw_dir: Path) -> list[dict[str, Any]]:
    official_records = import_official_cara_records(raw_dir)
    if official_records:
        return official_records

    roots = [raw_dir]
    extracted = raw_dir / "extracted"
    if extracted.exists():
        roots.insert(0, extracted)

    rows: list[dict[str, Any]] = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.suffix.lower() not in {".csv", ".tsv", ".txt", ".parquet"}:
                continue
            frame = _read_table(path)
            if frame is None or frame.empty:
                continue
            columns = {
                "assay_id": _find_column(
                    frame.columns,
                    [
                        "assay_id",
                        "assay",
                        "task_id",
                        "target_id",
                        "assay_chembl_id",
                        "chembl_assay_id",
                    ],
                ),
                "compound_id": _find_column(
                    frame.columns,
                    [
                        "compound_id",
                        "molecule_chembl_id",
                        "molregno",
                        "mol_id",
                        "cid",
                        "chembl_id",
                        "id",
                        "drug_id",
                    ],
                ),
                "smiles": _find_column(
                    frame.columns,
                    [
                        "smiles",
                        "canonical_smiles",
                        "compound_iso_smiles",
                        "isomeric_smiles",
                        "SMILES",
                    ],
                ),
                "activity": _find_column(
                    frame.columns,
                    [
                        "pchembl_value",
                        "standard_value",
                        "pIC50",
                        "pic50",
                        "activity_value",
                        "affinity",
                        "label",
                        "y",
                    ],
                ),
                "split": _find_column(frame.columns, ["split", "subset", "role", "set"]),
                "target": _find_column(
                    frame.columns,
                    ["target", "target_id", "target_chembl_id", "protein", "protein_id"],
                ),
            }
            if columns["smiles"] is None or columns["activity"] is None:
                continue
            for _, row in frame.iterrows():
                record = _candidate_record_from_row(row, columns, path)
                if record is not None:
                    rows.append(record)
    return rows


def write_imported_records(raw_dir: Path, out: Path, *, split_name: str = "LO_All") -> list[dict[str, Any]]:
    records = import_official_cara_records(raw_dir, split_name=split_name)
    importer = "official_cara_split" if records else "generic_tables"
    if not records:
        records = import_cara_records(raw_dir)
    write_jsonl(out, records)
    source_files = sorted({str(record.get("source_file")) for record in records if record.get("source_file")})
    metadata = {
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(raw_dir),
        "num_records": len(records),
        "num_assays": len({record.get("assay_id") for record in records}),
        "source_files": source_files,
        "layout_summary_path": str(out.with_suffix(".layout.json")),
        "importer": importer,
        "split_name": split_name if importer == "official_cara_split" else None,
    }
    write_json(out.with_suffix(".meta.json"), metadata)
    write_json(out.with_suffix(".layout.json"), inspect_cara_layout(raw_dir))
    return records


def _sanitize_id(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return sanitized[:80] or "assay"


def _load_constraints(path: Path | None) -> list[ConstraintSpec]:
    if path is None:
        return default_constraints()
    import json

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [ConstraintSpec.model_validate(row) for row in payload]


def _compound_from_record(record: dict[str, Any], prefix: str, index: int) -> CompoundRecord | None:
    smiles = str(record["smiles"])
    descriptors = compute_descriptors(smiles)
    if descriptors.get("valid_smiles") is False:
        return None
    compound_id = str(record.get("compound_id") or f"{prefix}_{index:06d}")
    return CompoundRecord(
        id=compound_id,
        smiles=smiles,
        activity_value=float(record["activity_value"]),
        descriptors=descriptors,
        metadata={
            "source_file": record.get("source_file"),
            "role": record.get("role"),
            "target": record.get("target"),
            "task_kind": record.get("task_kind"),
        },
    )


def build_decision_cards(
    records: list[dict[str, Any]],
    *,
    target_cards: int = 50,
    budget_k: int = 10,
    support_size: int = 50,
    min_support: int = 3,
    min_candidates: int | None = None,
    seed: int = 7,
    constraints_path: Path | None = None,
) -> list[DecisionCard]:
    # Deterministic grouping/sorting is used; seed is retained in metadata for reproducibility.
    min_candidates = min_candidates or budget_k
    constraints = _load_constraints(constraints_path)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("assay_id") or "unknown")].append(record)

    cards: list[DecisionCard] = []
    for assay_id, assay_records in sorted(grouped.items()):
        sorted_records = sorted(
            assay_records,
            key=lambda row: (str(row.get("role") or ""), str(row.get("compound_id") or "")),
        )
        explicit_support = [row for row in sorted_records if row.get("role") == "support"]
        explicit_candidates = [row for row in sorted_records if row.get("role") == "candidate"]
        if explicit_support and explicit_candidates:
            support_rows = explicit_support[:support_size]
            candidate_rows = explicit_candidates
        else:
            support_rows = sorted_records[:support_size]
            candidate_rows = sorted_records[support_size:]

        if len(support_rows) < min_support or len(candidate_rows) < min_candidates:
            continue

        support: list[CompoundRecord] = []
        for index, record in enumerate(support_rows):
            compound = _compound_from_record(record, "S", index)
            if compound is not None:
                support.append(compound)

        candidates: list[CompoundRecord] = []
        seen_candidate_ids: set[str] = set()
        support_ids = {compound.id for compound in support}
        for index, record in enumerate(candidate_rows):
            compound = _compound_from_record(record, "C", index)
            if compound is None:
                continue
            if compound.id in seen_candidate_ids or compound.id in support_ids:
                compound = compound.model_copy(update={"id": f"{compound.id}_{index:06d}"})
            seen_candidate_ids.add(compound.id)
            candidates.append(compound)

        if len(support) < min_support or len(candidates) < min_candidates:
            continue

        card = DecisionCard(
            task_id=f"CARA_LO_{_sanitize_id(assay_id)}_{len(cards) + 1:04d}",
            assay_context=AssayContext(assay_id=str(assay_id), source="CARA"),
            support_set=support,
            candidate_pool=candidates,
            budget_k=budget_k,
            hard_constraints=constraints,
            output_schema={
                "rank": "integer",
                "candidate_id": "string",
                "confidence": "optional number",
            },
            metadata={
                "source": "CARA",
                "assay_id": assay_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "support_size": len(support),
                "candidate_pool_size": len(candidates),
                "seed": seed,
            },
        )
        feasible_count = len(feasible_candidates(card))
        card.metadata["feasible_candidate_count"] = feasible_count
        if feasible_count < budget_k:
            continue
        cards.append(card)
        if len(cards) >= target_cards:
            break
    return cards


def build_cards_from_jsonl(
    records_path: Path,
    out: Path,
    *,
    target_cards: int = 50,
    budget_k: int = 10,
    support_size: int = 50,
    constraints_path: Path | None = None,
) -> list[DecisionCard]:
    cards = build_decision_cards(
        read_jsonl(records_path),
        target_cards=target_cards,
        budget_k=budget_k,
        support_size=support_size,
        constraints_path=constraints_path,
    )
    ensure_parent(out)
    write_jsonl(out, cards)
    write_json(
        out.with_suffix(".meta.json"),
        {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "records_path": str(records_path),
            "num_cards": len(cards),
            "target_cards": target_cards,
            "budget_k": budget_k,
            "support_size": support_size,
            "constraints_path": str(constraints_path) if constraints_path else None,
        },
    )
    return cards
