from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .data.cara import build_cards_from_jsonl, download_cara as download_cara_data
from .data.cara import inspect_cara_layout
from .data.cara import summarize_cards as summarize_card_models
from .data.cara import write_imported_records
from .io import load_models, write_json
from .reports import compare_run_summaries, make_frontier_plot, write_results_summary
from .runner import run_system_file
from .schemas import DecisionCard
from .scoring import score_run
from .systems import DETERMINISTIC_SYSTEMS, LLM_SYSTEMS
from .systems.llm import export_llm_requests as export_llm_request_rows
from .validation import validate_card_semantics

app = typer.Typer(help="SpecGuard-Chem v2 constrained prioritisation harness.")
console = Console()


def _expand_systems(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return sorted(DETERMINISTIC_SYSTEMS - {"oracle_valid_topk"}) + sorted(LLM_SYSTEMS)
    if value.strip().lower() == "all-with-oracle":
        return sorted(DETERMINISTIC_SYSTEMS) + sorted(LLM_SYSTEMS)
    return [name.strip() for name in value.split(",") if name.strip()]


@app.command("list-systems")
def list_systems() -> None:
    console.print("[bold]Deterministic systems[/bold]")
    for name in sorted(DETERMINISTIC_SYSTEMS):
        console.print(f"- {name}")
    console.print("[bold]LLM systems[/bold]")
    for name in sorted(LLM_SYSTEMS):
        console.print(f"- {name}")


@app.command("download-cara")
def download_cara(
    out: Path = typer.Option(Path("data/raw/cara"), "--out", "-o"),
    url: str = typer.Option(
        "https://zenodo.org/records/14740896/files/CARA.zip?download=1",
        "--url",
        help="CARA archive URL.",
    ),
    max_attempts: int = typer.Option(8, "--max-attempts"),
) -> None:
    provenance = download_cara_data(out, url=url, max_attempts=max_attempts)
    console.print(f"Downloaded CARA archive to [green]{provenance['archive_path']}[/green]")
    console.print(f"SHA256: [green]{provenance['archive_sha256']}[/green]")


@app.command("import-cara")
def import_cara(
    raw_dir: Path = typer.Argument(..., help="Directory containing CARA files or downloaded archive."),
    out: Path = typer.Option(Path("data/interim/cara_records.jsonl"), "--out", "-o"),
    split_name: str = typer.Option("LO_All", "--split-name", help="Official CARA split name."),
) -> None:
    records = write_imported_records(raw_dir, out, split_name=split_name)
    console.print(f"Imported [green]{len(records)}[/green] normalized records to [green]{out}[/green]")


@app.command("inspect-cara")
def inspect_cara(
    raw_dir: Path = typer.Argument(..., help="Directory containing CARA files or downloaded archive."),
    out: Path = typer.Option(Path("data/interim/cara_layout.json"), "--out", "-o"),
) -> None:
    summary = inspect_cara_layout(raw_dir)
    write_json(out, summary)
    console.print(f"Inspected [green]{len(summary['tables'])}[/green] table-like files -> {out}")


@app.command("build-cards")
def build_cards(
    records: Path = typer.Argument(..., help="Normalized CARA-like JSONL records."),
    out: Path = typer.Option(Path("data/cards/cara_lo_cards.jsonl"), "--out", "-o"),
    target_cards: int = typer.Option(50, "--target-cards"),
    budget_k: int = typer.Option(10, "--budget-k"),
    support_size: int = typer.Option(50, "--support-size"),
    constraints: Optional[Path] = typer.Option(None, "--constraints"),
    selection_policy: str = typer.Option("first", "--selection-policy"),
) -> None:
    cards = build_cards_from_jsonl(
        records,
        out,
        target_cards=target_cards,
        budget_k=budget_k,
        support_size=support_size,
        constraints_path=constraints,
        selection_policy=selection_policy,
    )
    console.print(f"Built [green]{len(cards)}[/green] decision cards at [green]{out}[/green]")


@app.command("summarize-cards")
def summarize_cards(
    cards: Path = typer.Argument(..., help="Decision-card JSONL path."),
    out: Optional[Path] = typer.Option(None, "--out", "-o"),
) -> None:
    loaded = load_models(cards, DecisionCard)
    summary = summarize_card_models(loaded)
    if out is not None:
        write_json(out, summary)
        console.print(f"Wrote card summary to [green]{out}[/green]")
    else:
        console.print_json(data=summary)


@app.command("validate-cards")
def validate_cards(cards: Path = typer.Argument(..., help="Decision-card JSONL path.")) -> None:
    loaded = load_models(cards, DecisionCard)
    issues = []
    for card in loaded:
        for issue in validate_card_semantics(card):
            issues.append((card.task_id, issue))
    if issues:
        for task_id, issue in issues[:20]:
            console.print(f"[red]{task_id}[/red] {issue.code}: {issue.message}")
        if len(issues) > 20:
            console.print(f"[red]... {len(issues) - 20} more issues[/red]")
        raise typer.Exit(code=1)
    console.print(f"Validated [green]{len(loaded)}[/green] decision cards")


@app.command("run-system")
def run_system(
    cards: Path = typer.Argument(..., help="Decision-card JSONL path."),
    system: str = typer.Option(..., "--system", "-s"),
    out: Path = typer.Option(Path("runs/run/trace.jsonl"), "--out", "-o"),
    seed: int = typer.Option(7, "--seed"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    allow_external: bool = typer.Option(False, "--allow-external"),
    model: str = typer.Option("gpt-4.1-mini", "--model"),
) -> None:
    records = run_system_file(
        cards,
        system,
        out,
        seed=seed,
        cache_dir=cache_dir,
        allow_external=allow_external,
        model=model,
    )
    console.print(f"Ran [green]{system}[/green] on [green]{len(records)}[/green] cards -> {out}")


@app.command("run-suite")
def run_suite(
    cards: Path = typer.Argument(..., help="Decision-card JSONL path."),
    systems: str = typer.Option(
        "random_valid,rules_only,similarity_to_best_active,qsar_rf",
        "--systems",
        help="Comma-separated system names.",
    ),
    out: Path = typer.Option(Path("runs/suite"), "--out", "-o"),
    seed: int = typer.Option(7, "--seed"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    allow_external: bool = typer.Option(False, "--allow-external"),
    model: str = typer.Option("gpt-4.1-mini", "--model"),
) -> None:
    names = _expand_systems(systems)
    manifest = {
        "cards": str(cards),
        "systems": names,
        "seed": seed,
        "allow_external": allow_external,
        "model": model,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "runs": [],
    }
    for name in names:
        run_path = out / name / "trace.jsonl"
        run_system_file(
            cards,
            name,
            run_path,
            seed=seed,
            cache_dir=(cache_dir / name if cache_dir else None),
            allow_external=allow_external,
            model=model,
        )
        scores_dir = out / name / "scores"
        score_run(cards, run_path, scores_dir)
        manifest["runs"].append({"system_name": name, "trace": str(run_path), "scores": str(scores_dir)})
        console.print(f"Completed [green]{name}[/green]")
    write_json(out / "manifest.json", manifest)
    console.print(f"Suite manifest written to [green]{out / 'manifest.json'}[/green]")


@app.command("export-llm-requests")
def export_llm_requests(
    cards: Path = typer.Argument(..., help="Decision-card JSONL path."),
    systems: str = typer.Option(
        "bare_llm,llm_validator,llm_tools,llm_tools_validator",
        "--systems",
        help="Comma-separated LLM system names.",
    ),
    out: Path = typer.Option(Path("runs/llm_requests.jsonl"), "--out", "-o"),
) -> None:
    from .io import write_jsonl

    loaded = load_models(cards, DecisionCard)
    names = [name.strip() for name in systems.split(",") if name.strip()]
    rows = export_llm_request_rows(loaded, names)
    write_jsonl(out, rows)
    console.print(f"Exported [green]{len(rows)}[/green] LLM requests -> {out}")


@app.command("score-run")
def score_run_command(
    cards: Path = typer.Argument(..., help="Decision-card JSONL path."),
    run: Path = typer.Argument(..., help="Run trace JSONL path."),
    out: Path = typer.Option(Path("runs/scores"), "--out", "-o"),
    hit_threshold: Optional[float] = typer.Option(None, "--hit-threshold"),
    bootstrap_samples: int = typer.Option(1000, "--bootstrap-samples"),
    seed: int = typer.Option(7, "--seed"),
) -> None:
    scores = score_run(
        cards,
        run,
        out,
        hit_threshold=hit_threshold,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    console.print(f"Scored [green]{len(scores)}[/green] records -> {out}")


@app.command("compare-runs")
def compare_runs(
    summaries: list[Path] = typer.Argument(..., help="One or more summary.json files."),
    out: Path = typer.Option(Path("paper/tables"), "--out", "-o"),
) -> None:
    frame = compare_run_summaries(summaries, out)
    console.print(f"Wrote comparison for [green]{len(frame)}[/green] systems -> {out}")


@app.command("make-figures")
def make_figures(
    comparison_csv: Path = typer.Argument(..., help="system_comparison.csv path."),
    out: Path = typer.Option(Path("paper/figures"), "--out", "-o"),
) -> None:
    output = make_frontier_plot(comparison_csv, out)
    console.print(f"Wrote frontier plot to [green]{output}[/green]")


@app.command("make-report")
def make_report(
    comparison_csv: Path = typer.Argument(..., help="system_comparison.csv path."),
    out: Path = typer.Option(Path("paper"), "--out", "-o"),
    title: str = typer.Option("SpecGuard-Chem v2 Results Summary", "--title"),
) -> None:
    output = write_results_summary(comparison_csv, out, title=title)
    console.print(f"Wrote results summary to [green]{output}[/green]")


if __name__ == "__main__":
    app()
