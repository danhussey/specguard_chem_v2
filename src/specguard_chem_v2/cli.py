from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .costing import (
    enforce_cost_limits,
    estimate_llm_matrix_cost,
    load_pricing_config,
    trace_is_complete,
)
from .data.cara import build_cards_from_jsonl, inspect_cara_layout, write_imported_records
from .data.cara import download_cara as download_cara_data
from .data.cara import summarize_cards as summarize_card_models
from .io import load_models, write_json
from .reports import (
    compare_run_summaries,
    make_frontier_plot,
    write_results_dashboard,
    write_results_summary,
)
from .runner import run_system_file
from .schemas import DecisionCard
from .scoring import score_run
from .systems import DETERMINISTIC_SYSTEMS, LLM_SYSTEMS
from .systems.llm import export_llm_requests as export_llm_request_rows
from .systems.providers import load_model_matrix, select_model_configs
from .validation import validate_card_semantics

app = typer.Typer(help="SpecGuard-Chem v2 constrained prioritisation harness.")
console = Console()


def _expand_systems(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return sorted(DETERMINISTIC_SYSTEMS - {"oracle_valid_topk"}) + sorted(LLM_SYSTEMS)
    if value.strip().lower() == "all-with-oracle":
        return sorted(DETERMINISTIC_SYSTEMS) + sorted(LLM_SYSTEMS)
    return [name.strip() for name in value.split(",") if name.strip()]


def _expand_llm_systems(value: str) -> list[str]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    unknown = [name for name in names if name not in LLM_SYSTEMS]
    if unknown:
        raise typer.BadParameter(f"Unknown LLM systems: {', '.join(unknown)}")
    return names


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
    workers: int = typer.Option(1, "--workers", min=1, help="Card-level worker count."),
) -> None:
    records = run_system_file(
        cards,
        system,
        out,
        seed=seed,
        cache_dir=cache_dir,
        allow_external=allow_external,
        model=model,
        workers=workers,
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
    workers: int = typer.Option(1, "--workers", min=1, help="Card-level worker count."),
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
            workers=workers,
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
    model_matrix: Optional[Path] = typer.Option(None, "--model-matrix"),
    model_conditions: str = typer.Option("all", "--model-conditions"),
) -> None:
    from .io import write_jsonl

    loaded = load_models(cards, DecisionCard)
    names = [name.strip() for name in systems.split(",") if name.strip()]
    configs = None
    if model_matrix is not None:
        configs = select_model_configs(load_model_matrix(model_matrix), model_conditions)
    rows = export_llm_request_rows(loaded, names, model_configs=configs)
    write_jsonl(out, rows)
    console.print(f"Exported [green]{len(rows)}[/green] LLM requests -> {out}")


@app.command("estimate-llm-cost")
def estimate_llm_cost(
    cards: Path = typer.Argument(..., help="Decision-card JSONL path."),
    systems: str = typer.Option(
        "bare_llm,llm_validator,llm_tools,llm_tools_validator",
        "--systems",
        help="Comma-separated LLM system names.",
    ),
    model_matrix: Path = typer.Option(Path("configs/model_matrix.toml"), "--model-matrix"),
    model_conditions: str = typer.Option("all", "--model-conditions"),
    pricing: Path = typer.Option(Path("configs/provider_pricing.toml"), "--pricing"),
    out_run_dir: Path = typer.Option(
        Path("runs/llm_matrix"),
        "--out-run-dir",
        help="Run directory used for completed-trace and default-cache detection.",
    ),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    out: Optional[Path] = typer.Option(None, "--out", "-o"),
    force: bool = typer.Option(False, "--force", help="Ignore completed traces when estimating."),
) -> None:
    loaded = load_models(cards, DecisionCard)
    names = _expand_llm_systems(systems)
    configs = select_model_configs(load_model_matrix(model_matrix), model_conditions)
    effective_cache_dir = cache_dir or (out_run_dir / "cache")
    estimate = estimate_llm_matrix_cost(
        loaded,
        names,
        configs,
        pricing=load_pricing_config(pricing),
        cache_dir=effective_cache_dir,
        run_out=out_run_dir,
        force=force,
    )
    if out is not None:
        write_json(out, estimate)
        console.print(f"Wrote cost estimate to [green]{out}[/green]")
    printable = {key: value for key, value in estimate.items() if key != "rows"}
    console.print_json(data=printable)


@app.command("list-model-matrix")
def list_model_matrix(
    model_matrix: Path = typer.Argument(Path("configs/model_matrix.toml")),
) -> None:
    configs = load_model_matrix(model_matrix)
    for config in configs.values():
        console.print(
            f"[bold]{config.id}[/bold] provider={config.provider} "
            f"model={config.model} tier={config.tier}"
        )


@app.command("run-llm-matrix")
def run_llm_matrix(
    cards: Path = typer.Argument(..., help="Decision-card JSONL path."),
    systems: str = typer.Option(
        "bare_llm,llm_validator,llm_tools,llm_tools_validator",
        "--systems",
        help="Comma-separated LLM system names.",
    ),
    model_matrix: Path = typer.Option(Path("configs/model_matrix.toml"), "--model-matrix"),
    model_conditions: str = typer.Option("all", "--model-conditions"),
    out: Path = typer.Option(Path("runs/llm_matrix"), "--out", "-o"),
    seed: int = typer.Option(7, "--seed"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    allow_external: bool = typer.Option(False, "--allow-external"),
    workers: int = typer.Option(1, "--workers", min=1, help="Card-level worker count."),
    pricing: Path = typer.Option(Path("configs/provider_pricing.toml"), "--pricing"),
    require_cost_estimate: bool = typer.Option(
        False,
        "--require-cost-estimate",
        help="Write and enforce a cost estimate before live calls.",
    ),
    max_estimated_cost_usd: Optional[float] = typer.Option(
        None,
        "--max-estimated-cost-usd",
        min=0,
        help="Abort if missing live calls exceed this estimated incremental cost.",
    ),
    max_live_calls: Optional[int] = typer.Option(
        None,
        "--max-live-calls",
        min=0,
        help="Abort if more than this many calls would need live provider execution.",
    ),
    max_input_tokens_per_call: Optional[int] = typer.Option(
        None,
        "--max-input-tokens-per-call",
        min=1,
        help="Abort if any missing live call is estimated above this input-token count.",
    ),
    force: bool = typer.Option(False, "--force", help="Rerun completed traces instead of skipping."),
) -> None:
    names = _expand_llm_systems(systems)
    configs = select_model_configs(load_model_matrix(model_matrix), model_conditions)
    effective_cache_dir = cache_dir or (out / "cache")
    loaded_cards = load_models(cards, DecisionCard)
    if allow_external and (
        require_cost_estimate
        or max_estimated_cost_usd is not None
        or max_live_calls is not None
        or max_input_tokens_per_call is not None
    ):
        estimate = estimate_llm_matrix_cost(
            loaded_cards,
            names,
            configs,
            pricing=load_pricing_config(pricing),
            cache_dir=effective_cache_dir,
            run_out=out,
            force=force,
        )
        write_json(out / "cost_estimate.json", estimate)
        failures = enforce_cost_limits(
            estimate,
            max_estimated_cost_usd=max_estimated_cost_usd,
            max_live_calls=max_live_calls,
            max_input_tokens_per_call=max_input_tokens_per_call,
        )
        printable = {key: value for key, value in estimate.items() if key != "rows"}
        console.print("[bold]Cost estimate[/bold]")
        console.print_json(data=printable)
        if failures:
            for failure in failures:
                console.print(f"[red]Cost gate failed:[/red] {failure}")
            raise typer.Exit(code=2)
    manifest = {
        "cards": str(cards),
        "systems": names,
        "model_matrix": str(model_matrix),
        "model_conditions": [config.id for config in configs],
        "seed": seed,
        "allow_external": allow_external,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "runs": [],
    }
    for config in configs:
        for system_name in names:
            run_label = f"{system_name}__{config.id}"
            run_path = out / config.id / system_name / "trace.jsonl"
            scores_dir = out / config.id / system_name / "scores"
            skipped_existing = False
            if not force and trace_is_complete(run_path, len(loaded_cards)):
                skipped_existing = True
                console.print(f"Skipping completed [green]{run_label}[/green]")
            else:
                run_system_file(
                    cards,
                    system_name,
                    run_path,
                    seed=seed,
                    cache_dir=effective_cache_dir / config.id / system_name,
                    allow_external=allow_external,
                    model_config=config,
                    run_label=run_label,
                    workers=workers,
                )
            score_run(cards, run_path, scores_dir)
            manifest["runs"].append(
                {
                    "system_name": system_name,
                    "run_label": run_label,
                    "model_config_id": config.id,
                    "provider": config.provider,
                    "model": config.model,
                    "trace": str(run_path),
                    "scores": str(scores_dir),
                    "skipped_existing": skipped_existing,
                }
            )
            console.print(f"Completed [green]{run_label}[/green]")
    write_json(out / "manifest.json", manifest)
    console.print(f"Matrix manifest written to [green]{out / 'manifest.json'}[/green]")


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


@app.command("make-dashboard")
def make_dashboard(
    comparison_csv: Path = typer.Argument(..., help="system_comparison.csv path."),
    out: Path = typer.Option(Path("paper"), "--out", "-o"),
    title: str = typer.Option("SpecGuard-Chem v2 Results Dashboard", "--title"),
) -> None:
    output = write_results_dashboard(comparison_csv, out, title=title)
    console.print(f"Wrote results dashboard to [green]{output}[/green]")


if __name__ == "__main__":
    app()
